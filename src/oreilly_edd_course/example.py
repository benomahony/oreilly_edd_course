"""
Eval-Driven Development: one fully worked example.

Extract action items from meeting transcripts, measure how well we do it, then let
an improver agent fix the failures:

  - Prompt — rewrite the extraction instructions (instructions.md)
  - Capability — author tools, guardrails or hooks with pydantic-ai-harness
    `CapabilityCreation`, written to capabilities/ and live on the extractor's next run.
    The extractor carries CapabilityCreation too, so it can author its own.

Review what changed with `git diff`; commit to keep it.

Lexguard word lists do double duty: the same lexicon is an offline eval
(does the output contain vague / hypothetical / leaked wording?) and a
runtime guardrail (reject it and make the model retry).

Flow:
  1. The system under test      — Pydantic models + extraction agent + lexguard guardrails
  2. The golden dataset          — transcripts + expected outputs
  3. The evals                   — schema → deterministic → lexguard → reference → LLM judge → operational
  4. The improver                — prompt rewrite + capability creation
  5. The loop                    — eval → improve → re-eval, then diff against the baseline
"""

import asyncio
import os
import shutil
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator
from pydantic_ai import Agent
from lexguard import (
    Bloat,
    Completion,
    ConditionalTrigger,
    Confidential,
    Hedging,
    Hypothetical,
    Injection,
    Leakage,
    Overreach,
    Past,
    Servility,
    Vague,
)
from lexguard.integrations.evals.pydantic_evals import LexguardEvaluator
from lexguard.integrations.guardrails.pydantic_ai import lexguard_guard
from pydantic_ai_harness.capability_creation import CapabilityCreation
from pydantic_ai_harness.guardrails import GuardrailResult, InputBlocked, InputGuardrail, OutputGuardrail
from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import (
    EvaluationReason,
    Evaluator,
    EvaluatorContext,
    IsInstance,
    LLMJudge,
    MaxDuration,
    MaxModelRequests,
)
from pydantic_evals.online import OnlineEvaluator
from pydantic_evals.online_capability import OnlineEvaluation
from pydantic_evals.reporting import EvaluationReport

from oreilly_edd_course.providers import Settings, get_model
from oreilly_edd_course.telemetry import init_telemetry
from oreilly_edd_course.lexicons import StatusUpdate, TodoVerb, VagueOwner

model = get_model()

HERE = Path(__file__).parent
TRANSCRIPTS = HERE / "transcripts"
MAX_ITERATIONS = 3
# What gets improved — committed to git, so every improvement is a reviewable diff.
INSTRUCTIONS_PATH = HERE / "instructions.md"
CAPABILITIES_DIR = HERE / "capabilities"

# Deliberately naive starting point (`--fresh` resets to it) — the evals will tell us what's missing.
BASELINE_INSTRUCTIONS = "Extract the action items from this meeting transcript."


# ═══ 1. The system under test ══════════════════════════════════════════════
# The schema is the first eval: the agent retries until the output validates.


class Todo(BaseModel):
    who: str = Field(description="Full name of the person responsible", min_length=1)
    what: str = Field(description="The action to take, understandable on its own")
    when: date = Field(description="Due date")
    criticality: Literal["high", "medium", "low"]


class MeetingTodos(BaseModel):
    todos: list[Todo]
    meeting_date: date
    attendees: list[str] = Field(description="Full names of everyone who spoke")

    @field_validator("meeting_date")
    @classmethod
    def meeting_date_is_plausible(cls, v: date) -> date:
        assert date(2020, 1, 1) <= v <= date(2030, 1, 1), f"{v} is not a plausible meeting date"
        return v


# ── Lexguard lexicons: plain word matching, no model in the loop ──
# Each (lexicon, Todo field it checks). Shipped lexicons catch wording that turns a
# todo into a non-todo; our own (lexicons.py) add the meeting-specific rules.
TODO_LEXICONS = [
    *[(lexicon, "what") for lexicon in (Vague, Hypothetical, Completion, ConditionalTrigger, Past, Hedging)],
    (TodoVerb, "what"),  # custom: must start with an action (extends lexguard's Actionable)
    (StatusUpdate, "what"),  # custom: status reports aren't todos
    (VagueOwner, "who"),  # custom: "the team" / "we" owns nothing
]
# Wording that should never appear anywhere in the output.
NEVER_IN_OUTPUT = Leakage  # SelfReference, SystemLeak, Injection, Placeholder


def todo_lexicon_failures(output: MeetingTodos) -> dict[str, list[str]]:
    """Per lexicon, the lexguard reason for every todo that fails it."""
    failures: dict[str, list[str]] = {lexicon.label: [] for lexicon, _ in TODO_LEXICONS}
    for todo in output.todos:
        for lexicon, field in TODO_LEXICONS:
            text = getattr(todo, field)
            verdict = lexicon.verdict(text)
            if not verdict.passed:
                failures[lexicon.label].append(f"{field}={text!r}: {verdict.reason}")
    return failures


def todo_wording_guard(output: MeetingTodos) -> GuardrailResult:
    """The same check as the TodoWording eval, enforced at runtime."""
    reasons = [r for rs in todo_lexicon_failures(output).values() for r in rs]
    return GuardrailResult.retry("\n".join(reasons)) if reasons else GuardrailResult.allow()


def block_injection(transcript: str) -> GuardrailResult:
    """Raise rather than return GuardrailResult.block(): a block is a text refusal, which a
    structured-output agent treats as invalid output and retries — straight past the guard."""
    verdict = Injection.verdict(transcript)
    if not verdict.passed:
        raise InputBlocked(verdict.reason)
    return GuardrailResult.allow()


# ── Guardrails the developer ships: always on ──
GUARDRAILS = [
    # A transcript that tries to instruct the model is rejected before any model call.
    # Not Confidential: client_onboarding legitimately discusses SSO "credentials".
    InputGuardrail(guard=block_injection),
    # Leaked prompts / AI self-talk / placeholders in the output: retry with lexguard's fix.
    OutputGuardrail(guard=lexguard_guard(NEVER_IN_OUTPUT)),
]
# Opt-in: enforce the per-todo lexicons at runtime too. Off by default so the
# baseline shows what the evals catch; flip it on to compare the retry cost.
ENFORCE_TODO_WORDING = False
if ENFORCE_TODO_WORDING:
    GUARDRAILS.append(OutputGuardrail(guard=todo_wording_guard))

# Authored capabilities (by the improver or the extractor itself) live here. `store.load_active()` imports
# every active one so we can thread it into the next run.
creation = CapabilityCreation(directory=CAPABILITIES_DIR)

# The agent under test can author capabilities too: whatever it writes is live on its next run.
extractor = Agent(model, output_type=MeetingTodos, retries=4, capabilities=[*GUARDRAILS, creation])


async def extract_todos(transcript: str) -> MeetingTodos:
    result = await extractor.run(
        transcript,
        instructions=INSTRUCTIONS_PATH.read_text(),
        capabilities=[online_evals, *creation.store.load_active()],
    )
    return result.output


# ═══ 2. The golden dataset ═════════════════════════════════════════════════


def load_transcript(name: str) -> str:
    # 1.txt has "# Action Item" annotations — strip them so we don't leak the answers.
    lines = (TRANSCRIPTS / name).read_text().splitlines()
    return "\n".join(line for line in lines if not line.startswith("#"))


cases = [
    Case(
        name="engineering_standup",
        inputs=load_transcript("1.txt"),
        expected_output=MeetingTodos(
            meeting_date=date(2026, 1, 9),
            attendees=["Sarah Chen", "Marcus Rodriguez", "Alex Kim", "Priya Patel"],
            todos=[
                Todo(who="Alex Kim", what="Send Redis cluster details to Marcus Rodriguez", when=date(2026, 1, 9), criticality="high"),
                Todo(who="Alex Kim", what="Send connection pooling config to Marcus Rodriguez", when=date(2026, 1, 9), criticality="high"),
                Todo(who="Sarah Chen", what="Ping design team about final mockups", when=date(2026, 1, 9), criticality="medium"),
                Todo(who="Marcus Rodriguez", what="Review Priya's PR #847", when=date(2026, 1, 9), criticality="high"),
                Todo(who="Sarah Chen", what="Confirm Wednesday afternoon works for DB migration with Product", when=date(2026, 1, 10), criticality="medium"),
                Todo(who="Alex Kim", what="Schedule maintenance window for database migration", when=date(2026, 1, 9), criticality="medium"),
                Todo(who="Priya Patel", what="Create ticket for updating testing documentation", when=date(2026, 1, 9), criticality="low"),
            ],
        ),
    ),
    Case(
        name="product_planning",
        inputs=load_transcript("2.txt"),
        expected_output=MeetingTodos(
            meeting_date=date(2026, 1, 9),
            attendees=["Jennifer Walsh", "Maya Johnson", "Tom Richardson", "Kevin Martinez", "Lisa Anderson"],
            todos=[
                Todo(who="Kevin Martinez", what="Research data warehouse options with cost estimates and migration timeline", when=date(2026, 1, 16), criticality="high"),
                Todo(who="Tom Richardson", what="Sync with Kevin on technical integration points", when=date(2026, 1, 14), criticality="medium"),
                Todo(who="Maya Johnson", what="Set up requirements calls with 3 enterprise customers", when=date(2026, 1, 14), criticality="high"),
                Todo(who="Maya Johnson", what="Line up 2-3 customers for user testing session", when=date(2026, 1, 14), criticality="medium"),
            ],
        ),
    ),
    Case(
        name="client_onboarding",
        inputs=load_transcript("3.txt"),
        expected_output=MeetingTodos(
            meeting_date=date(2026, 1, 9),
            attendees=["Rachel Foster", "Amanda Chen", "Robert Park", "David Park"],
            todos=[
                Todo(who="Robert Park", what="Get Okta attribute schema from security team", when=date(2026, 1, 10), criticality="high"),
                Todo(who="Amanda Chen", what="Talk to marketing team about using their project as test case", when=date(2026, 1, 10), criticality="medium"),
                Todo(who="Amanda Chen", what="Request Jira admin access for Robert Park", when=date(2026, 1, 10), criticality="high"),
                Todo(who="Amanda Chen", what="Audit custom Jira fields and document what they're used for", when=date(2026, 1, 17), criticality="high"),
            ],
        ),
    ),
]


# ═══ 3. The evals ══════════════════════════════════════════════════════════
# Cheapest and most trustworthy first. Reference-free checks can become
# runtime guardrails (capabilities); reference-based ones only work offline.

Ctx = EvaluatorContext[str, MeetingTodos, None]


# ── Deterministic, reference-free (candidates for guardrails) ──


@dataclass
class NoDuplicateTodos(Evaluator[str, MeetingTodos, None]):
    def evaluate(self, ctx: Ctx) -> EvaluationReason:
        seen: set[tuple[str, str]] = set()
        for todo in ctx.output.todos:
            key = (todo.who.lower(), todo.what.lower())
            if key in seen:
                return EvaluationReason(False, f"Duplicate: {todo.who} / {todo.what}")
            seen.add(key)
        return EvaluationReason(True)


@dataclass
class AssigneesAreAttendees(Evaluator[str, MeetingTodos, None]):
    """Everyone assigned a todo must be in the attendee list (no invented people)."""

    def evaluate(self, ctx: Ctx) -> EvaluationReason:
        attendees = {a.lower() for a in ctx.output.attendees}
        strangers = sorted({t.who for t in ctx.output.todos if t.who.lower() not in attendees})
        if strangers:
            return EvaluationReason(False, f"Assignees not in attendees: {strangers}")
        return EvaluationReason(True)


@dataclass
class AttendeesInTranscript(Evaluator[str, MeetingTodos, None]):
    """Every attendee name appears in the transcript (no invented or misspelt people)."""

    def evaluate(self, ctx: Ctx) -> EvaluationReason:
        missing = [a for a in ctx.output.attendees if a not in ctx.inputs]
        if missing:
            return EvaluationReason(False, f"Not in transcript: {missing}")
        return EvaluationReason(True)


@dataclass
class DueDatesNotBeforeMeeting(Evaluator[str, MeetingTodos, None]):
    def evaluate(self, ctx: Ctx) -> EvaluationReason:
        early = [f"{t.what} ({t.when})" for t in ctx.output.todos if t.when < ctx.output.meeting_date]
        if early:
            return EvaluationReason(False, f"Due before meeting {ctx.output.meeting_date}: {early}")
        return EvaluationReason(True)


@dataclass
class ConciseTodos(Evaluator[str, MeetingTodos, None]):
    """House style: each todo fits on one line of a task tracker."""

    max_words: int = 12

    def evaluate(self, ctx: Ctx) -> EvaluationReason:
        long = [t.what for t in ctx.output.todos if len(t.what.split()) > self.max_words]
        if long:
            return EvaluationReason(False, f"Todos over {self.max_words} words: {long}")
        return EvaluationReason(True)


# ── Lexguard: the same lexicons as the guardrails, measured offline ──


@dataclass
class TodoWording(Evaluator[str, MeetingTodos, None]):
    """One assertion per lexicon, checked against every todo."""

    def evaluate(self, ctx: Ctx) -> dict[str, EvaluationReason]:
        return {
            label: EvaluationReason(not reasons, "; ".join(reasons) or None)
            for label, reasons in todo_lexicon_failures(ctx.output).items()
        }


# ── Jev: a typed judge — yes/no questions with a confidence each, no free text ──
# LLMJudge can't run on Jev (its output has a free-text `reason`), so ask typed questions instead.


class TodoJudgement(BaseModel):
    """Judge the todos extracted from this meeting transcript."""

    captures_every_commitment: bool = Field(
        description="Does the todo list include every action a person explicitly committed to or was assigned?"
    )
    invents_nothing: bool = Field(
        description="Is every todo something a person committed to or was assigned, rather than just discussed?"
    )
    owners_correct: bool = Field(
        description="Is each todo owned by the person who will do it, not the person it is for?"
    )


jev = Agent("typesafe:jev-latest", output_type=TodoJudgement) if os.environ.get("TYPESAFE_API_KEY") else None


@dataclass
class JevJudge(Evaluator[str, MeetingTodos, None]):
    async def evaluate(self, ctx: Ctx) -> dict[str, EvaluationReason]:
        assert jev is not None
        result = await jev.run(f"Transcript:\n{ctx.inputs}\n\nExtracted todos:\n{ctx.output.model_dump_json(indent=2)}")
        confidence = (result.response.provider_details or {}).get("confidence", {})
        return {
            f"Jev_{question}": EvaluationReason(answer, f"confidence {confidence.get(question, float('nan')):.2f}")
            for question, answer in result.output.model_dump().items()
        }


# ── Deterministic, reference-based (need the golden answer) ──


@dataclass
class MeetingDateCorrect(Evaluator[str, MeetingTodos, None]):
    def evaluate(self, ctx: Ctx) -> EvaluationReason:
        expected, actual = ctx.expected_output.meeting_date, ctx.output.meeting_date
        return EvaluationReason(actual == expected, f"expected {expected}, got {actual}")


@dataclass
class AttendeesMatch(Evaluator[str, MeetingTodos, None]):
    def evaluate(self, ctx: Ctx) -> EvaluationReason:
        expected = {a.lower() for a in ctx.expected_output.attendees}
        actual = {a.lower() for a in ctx.output.attendees}
        return EvaluationReason(
            actual == expected,
            f"missing {sorted(expected - actual)}, extra {sorted(actual - expected)}",
        )


@dataclass
class TodoCount(Evaluator[str, MeetingTodos, None]):
    def evaluate(self, ctx: Ctx) -> EvaluationReason:
        expected, actual = len(ctx.expected_output.todos), len(ctx.output.todos)
        return EvaluationReason(actual == expected, f"expected {expected} todos, got {actual}")


@dataclass
class OwnerRecall(Evaluator[str, MeetingTodos, None]):
    """Score: fraction of expected (who, when) pairs found in the output."""

    def evaluate(self, ctx: Ctx) -> EvaluationReason:
        remaining = [(t.who.lower(), t.when) for t in ctx.output.todos]
        missed = []
        for t in ctx.expected_output.todos:
            key = (t.who.lower(), t.when)
            if key in remaining:
                remaining.remove(key)
            else:
                missed.append(f"{t.who} by {t.when}: {t.what}")
        score = 1 - len(missed) / len(ctx.expected_output.todos)
        return EvaluationReason(round(score, 2), f"missed {missed}" if missed else "all found")


# ── Online: everything that doesn't need a golden answer also runs on every real run ──
quality_judge = LLMJudge(
    model=model,
    rubric="Each todo is specific, actionable, and understandable without reading the transcript.",
)
ONLINE_EVALUATORS = [
    # Deterministic, reference-free
    NoDuplicateTodos(),
    AttendeesInTranscript(),
    AssigneesAreAttendees(),
    DueDatesNotBeforeMeeting(),
    ConciseTodos(),
    # Lexguard: per-todo wording + whole-output prose / safety bundles
    TodoWording(),
    LexguardEvaluator(Bloat | Servility | Overreach),
    LexguardEvaluator(NEVER_IN_OUTPUT | Confidential),
    # LLM-as-judge on quality (no expected output needed)
    quality_judge,
    # Typed judge on Jev (~0.3s, confidence per answer) — needs TYPESAFE_API_KEY
    *([JevJudge()] if jev else []),
]
# Attached to the extractor: results go out as OTel `gen_ai.evaluation.result` events (see
# them in Logfire). Cheap checks run on every run; the LLM judge on a 10% sample.
# It skips itself inside Dataset.evaluate, so offline runs aren't evaluated twice.
online_evals = OnlineEvaluation(
    evaluators=[
        OnlineEvaluator(evaluator=e, sample_rate=0.1) if e is quality_judge else e for e in ONLINE_EVALUATORS
    ]
)

# ── Offline: the online evaluators plus the ones that need the golden answer ──
dataset = Dataset[str, MeetingTodos, None](
    name="meeting_todos",
    cases=cases,
    evaluators=[
        # Schema: did we even get the right type back?
        IsInstance(type_name="MeetingTodos"),
        *ONLINE_EVALUATORS,
        # Deterministic, reference-based
        MeetingDateCorrect(),
        AttendeesMatch(),
        TodoCount(),
        OwnerRecall(),
        # LLM-as-judge against the golden answer
        LLMJudge(
            model=model,
            rubric="The output covers every action item in the expected output and invents none.",
            include_input=True,
            include_expected_output=True,
        ),
        # Operational: latency and cost (retries from guardrails show up here).
        # A local model serves one case at a time, so each case waits for the others.
        MaxDuration(seconds=90 if Settings().provider == "google" else 1800),
        MaxModelRequests(max_requests=3),
    ],
)


def summarise_failures(report: EvaluationReport) -> list[str]:
    failures = [f"{f.name} › task crashed: {f.error_message}" for f in report.failures]
    for case in report.cases:
        for name, result in case.assertions.items():
            if not result.value:
                failures.append(f"{case.name} › {name}: {result.reason}")
        for name, result in case.scores.items():
            if result.value < 1:
                failures.append(f"{case.name} › {name}={result.value}: {result.reason}")
    return failures


# ═══ 4. The improver ═══════════════════════════════════════════════════════
# An agent reads the eval failures and pulls two levers: rewrite the prompt, or author
# capabilities (tools, guardrails, hooks). It also reviews what the extractor wrote for itself.


class PromptChange(BaseModel):
    instructions: str = Field(description="The full, updated extraction instructions")
    reason: str = Field(description="What you changed and why, including any capability you authored")


IMPROVER_INSTRUCTIONS = f"""\
You improve a meeting-transcript extraction agent based on eval failures.

1. PROMPT — return updated extraction instructions. Use this for judgement: what counts as
   an action item, owners, phrasing, dates and priorities. Make the minimum changes needed;
   keep what already works.

2. CAPABILITY — call `author_capability(name, code)` to give the extractor something a
   prompt can't: any pydantic-ai capability, live on its next run.
   - A TOOL (override `get_toolset`) when the model keeps getting something wrong that code
     gets right, e.g. date arithmetic or parsing speakers out of the transcript. Tools cost
     extra model requests, which MaxModelRequests measures.
   - A GUARDRAIL (override `after_output_validate`, raise ModelRetry) for a FAILING
     reference-free eval: NoDuplicateTodos, AttendeesInTranscript, AssigneesAreAttendees,
     DueDatesNotBeforeMeeting, ConciseTodos, or a lexguard lexicon (Vague, Hypothetical,
     Completion, Hedging, Slop... or our custom TodoVerb / StatusUpdate / VagueOwner).
     Promote a lexguard eval with the same lexicon: `lexicon.verdict(text)`, and pass
     `verdict.reason` (it includes lexguard's fix) to ModelRetry. Shipped lexicons come from
     `lexguard`, custom ones from `oreilly_edd_course.lexicons`.
   Don't re-author a capability that's already active.

3. REVIEW — the extractor can author capabilities for itself. Use
   `list_authored_capabilities` and `disable_authored_capability` on any that aren't helping.

Capability code must define exactly one AbstractCapability subclass with a no-argument
constructor. The output is a MeetingTodos object (use attribute access; don't import it).

A tool:

```python
from pydantic_ai.capabilities import AbstractCapability
from pydantic_ai.toolsets import FunctionToolset


def word_count(text: str) -> int:
    \'\'\'Count the words in a piece of text.\'\'\'
    return len(text.split())


class WordCountTool(AbstractCapability):
    def get_toolset(self):
        return FunctionToolset(tools=[word_count])
```

A guardrail promoted from a lexguard eval:

```python
from lexguard import Vague
from pydantic_ai.capabilities import AbstractCapability
from pydantic_ai.exceptions import ModelRetry


class NoVagueTodos(AbstractCapability):
    async def after_output_validate(self, ctx, *, output_context, output):
        for todo in output.todos:
            verdict = Vague.verdict(todo.what)
            if not verdict.passed:
                raise ModelRetry(f"Todo {{todo.what!r}}: {{verdict.reason}}")
        return output
```

The extractor's output schema:
{MeetingTodos.model_json_schema()}
"""

improver = Agent(model, output_type=PromptChange, instructions=IMPROVER_INSTRUCTIONS, capabilities=[creation])


async def improve(failures: list[str]) -> PromptChange:
    active = [c.name for c in creation.store.list_all() if c.status == "active" and not c.last_error]
    prompt = (
        f"Current instructions:\n{INSTRUCTIONS_PATH.read_text()}\n\n"
        f"Active capabilities: {active or 'none'}\n\n"
        "Eval failures:\n" + "\n".join(f"- {f}" for f in failures)
    )
    return (await improver.run(prompt)).output


# ═══ 5. The loop ═══════════════════════════════════════════════════════════


def reset() -> None:
    """Back to the naive prompt with no authored capabilities (`--fresh`)."""
    shutil.rmtree(CAPABILITIES_DIR, ignore_errors=True)
    INSTRUCTIONS_PATH.write_text(BASELINE_INSTRUCTIONS)


async def evaluate(label: str) -> EvaluationReport:
    # A local model serves one request at a time; running cases in parallel just queues them into timeouts.
    concurrency = None if Settings().provider == "google" else 1
    report = await dataset.evaluate(extract_todos, name=label, max_concurrency=concurrency)
    report.print(include_reasons=True)
    return report


async def main(fresh: bool = False) -> None:
    # Improvements accumulate: each run starts from the committed agent and builds on it.
    if fresh or not INSTRUCTIONS_PATH.exists():
        reset()
    baseline = await evaluate("baseline")
    report = baseline

    for iteration in range(1, MAX_ITERATIONS + 1):
        failures = summarise_failures(report)
        if not failures:
            print("\nAll evals pass.")
            break

        print(f"\n── Improving ({iteration}/{MAX_ITERATIONS}): {len(failures)} failure(s) ──")
        change = await improve(failures)
        INSTRUCTIONS_PATH.write_text(change.instructions)
        print(f"Reason: {change.reason}")
        for cap in creation.store.list_all():
            print(f"  capability {cap.name} [{cap.status}]{' ERROR: ' + cap.last_error if cap.last_error else ''}")

        report = await evaluate(f"iteration {iteration}")

    print("\n══ Baseline → final ══")
    report.print(baseline=baseline)
    print(f"\nReview what changed:  git diff {HERE.relative_to(Path.cwd())}")
    print("Commit to keep the improvements, or `git checkout` to throw them away.")


if __name__ == "__main__":
    init_telemetry(service_name="meeting-todos")
    asyncio.run(main(fresh="--fresh" in sys.argv))

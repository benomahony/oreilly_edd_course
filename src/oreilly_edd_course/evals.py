"""
The golden dataset and evals for the meeting-todos extractor in example.py.

Every reference-free evaluator runs twice: offline against the golden dataset, and
online on every real extraction, as OTel events you can see in Logfire.
"""

import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import cast, override

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from lexguard import (
    Bloat,
    Completion,
    ConditionalTrigger,
    Confidential,
    Hedging,
    Hypothetical,
    Leakage,
    Overreach,
    Past,
    Servility,
    Vague,
)
from lexguard.integrations.evals.pydantic_evals import LexguardEvaluator
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

from oreilly_edd_course.lexicons import StatusUpdate, TodoVerb, VagueOwner
from oreilly_edd_course.models import MeetingTodos, Todo

JUDGE_MODEL = "google:gemini-2.5-pro"

TRANSCRIPTS = Path(__file__).parent / "transcripts"


# ── Lexguard lexicons: plain word matching, no model in the loop ──
# Each (lexicon, Todo field it checks). Shipped lexicons catch wording that turns a
# todo into a non-todo; our own (lexicons.py) add the meeting-specific rules.
TODO_LEXICONS = [
    *[
        (lexicon, "what")
        for lexicon in (
            Vague,
            Hypothetical,
            Completion,
            ConditionalTrigger,
            Past,
            Hedging,
        )
    ],
    # custom: must start with an action (extends lexguard's Actionable)
    (TodoVerb, "what"),
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
            text = todo.what if field == "what" else todo.who
            verdict = lexicon.verdict(text)
            if not verdict.passed:
                failures[lexicon.label].append(f"{field}={text!r}: {verdict.reason}")
    return failures


# ═══ The golden dataset ═════════════════════════════════════════════════════


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
                Todo(
                    who="Alex Kim",
                    what="Send Redis cluster details to Marcus Rodriguez",
                    when=date(2026, 1, 9),
                    criticality="high",
                ),
                Todo(
                    who="Alex Kim",
                    what="Send connection pooling config to Marcus Rodriguez",
                    when=date(2026, 1, 9),
                    criticality="high",
                ),
                Todo(
                    who="Sarah Chen",
                    what="Ping design team about final mockups",
                    when=date(2026, 1, 9),
                    criticality="medium",
                ),
                Todo(
                    who="Marcus Rodriguez",
                    what="Review Priya's PR #847",
                    when=date(2026, 1, 9),
                    criticality="high",
                ),
                Todo(
                    who="Sarah Chen",
                    what="Confirm Wednesday afternoon works for DB migration with Product",
                    when=date(2026, 1, 10),
                    criticality="medium",
                ),
                Todo(
                    who="Alex Kim",
                    what="Schedule maintenance window for database migration",
                    when=date(2026, 1, 9),
                    criticality="medium",
                ),
                Todo(
                    who="Priya Patel",
                    what="Create ticket for updating testing documentation",
                    when=date(2026, 1, 9),
                    criticality="low",
                ),
            ],
        ),
    ),
    Case(
        name="product_planning",
        inputs=load_transcript("2.txt"),
        expected_output=MeetingTodos(
            meeting_date=date(2026, 1, 9),
            attendees=[
                "Jennifer Walsh",
                "Maya Johnson",
                "Tom Richardson",
                "Kevin Martinez",
                "Lisa Anderson",
            ],
            todos=[
                Todo(
                    who="Kevin Martinez",
                    what="Research data warehouse options with cost estimates and migration timeline",
                    when=date(2026, 1, 16),
                    criticality="high",
                ),
                Todo(
                    who="Tom Richardson",
                    what="Sync with Kevin on technical integration points",
                    when=date(2026, 1, 14),
                    criticality="medium",
                ),
                Todo(
                    who="Maya Johnson",
                    what="Set up requirements calls with 3 enterprise customers",
                    when=date(2026, 1, 14),
                    criticality="high",
                ),
                Todo(
                    who="Maya Johnson",
                    what="Line up 2-3 customers for user testing session",
                    when=date(2026, 1, 14),
                    criticality="medium",
                ),
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
                Todo(
                    who="Robert Park",
                    what="Get Okta attribute schema from security team",
                    when=date(2026, 1, 10),
                    criticality="high",
                ),
                Todo(
                    who="Amanda Chen",
                    what="Talk to marketing team about using their project as test case",
                    when=date(2026, 1, 10),
                    criticality="medium",
                ),
                Todo(
                    who="Amanda Chen",
                    what="Request Jira admin access for Robert Park",
                    when=date(2026, 1, 10),
                    criticality="high",
                ),
                Todo(
                    who="Amanda Chen",
                    what="Audit custom Jira fields and document what they're used for",
                    when=date(2026, 1, 17),
                    criticality="high",
                ),
            ],
        ),
    ),
]


# ═══ The evals ══════════════════════════════════════════════════════════════
# Cheapest and most trustworthy first. Reference-free checks can become
# runtime guardrails (capabilities); reference-based ones only work offline.

Ctx = EvaluatorContext[str, MeetingTodos, None]
TodoEvaluator = Evaluator[str, MeetingTodos, None]


# ── Deterministic, reference-free (candidates for guardrails) ──


@dataclass
class NoDuplicateTodos(TodoEvaluator):
    @override
    def evaluate(self, ctx: Ctx) -> EvaluationReason:
        seen: set[tuple[str, str]] = set()
        for todo in ctx.output.todos:
            key = (todo.who.lower(), todo.what.lower())
            if key in seen:
                return EvaluationReason(False, f"Duplicate: {todo.who} / {todo.what}")
            seen.add(key)
        return EvaluationReason(True)


@dataclass
class AssigneesAreAttendees(TodoEvaluator):
    """Everyone assigned a todo must be in the attendee list (no invented people)."""

    @override
    def evaluate(self, ctx: Ctx) -> EvaluationReason:
        attendees = {a.lower() for a in ctx.output.attendees}
        strangers = sorted(
            {t.who for t in ctx.output.todos if t.who.lower() not in attendees}
        )
        if strangers:
            return EvaluationReason(False, f"Assignees not in attendees: {strangers}")
        return EvaluationReason(True)


@dataclass
class AttendeesInTranscript(TodoEvaluator):
    """Every attendee name appears in the transcript (no invented or misspelt people)."""

    @override
    def evaluate(self, ctx: Ctx) -> EvaluationReason:
        missing = [a for a in ctx.output.attendees if a not in ctx.inputs]
        if missing:
            return EvaluationReason(False, f"Not in transcript: {missing}")
        return EvaluationReason(True)


@dataclass
class DueDatesNotBeforeMeeting(TodoEvaluator):
    @override
    def evaluate(self, ctx: Ctx) -> EvaluationReason:
        early = [
            f"{t.what} ({t.when})"
            for t in ctx.output.todos
            if t.when < ctx.output.meeting_date
        ]
        if early:
            return EvaluationReason(
                False, f"Due before meeting {ctx.output.meeting_date}: {early}"
            )
        return EvaluationReason(True)


@dataclass
class ConciseTodos(TodoEvaluator):
    """House style: each todo fits on one line of a task tracker."""

    max_words: int = 12

    @override
    def evaluate(self, ctx: Ctx) -> EvaluationReason:
        long = [
            t.what for t in ctx.output.todos if len(t.what.split()) > self.max_words
        ]
        if long:
            return EvaluationReason(False, f"Todos over {self.max_words} words: {long}")
        return EvaluationReason(True)


# ── Lexguard: the same lexicons as the guardrails, measured offline ──


@dataclass
class TodoWording(TodoEvaluator):
    """One assertion per lexicon, checked against every todo."""

    @override
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


jev = (
    Agent("typesafe:jev-latest", output_type=TodoJudgement)
    if os.environ.get("TYPESAFE_API_KEY")
    else None
)


@dataclass
class JevJudge(TodoEvaluator):
    @override
    async def evaluate(self, ctx: Ctx) -> dict[str, EvaluationReason]:
        assert jev is not None
        result = await jev.run(
            f"Transcript:\n{ctx.inputs}\n\nExtracted todos:\n{ctx.output.model_dump_json(indent=2)}"
        )
        details = result.response.provider_details or {}
        confidence = cast(dict[str, float], details.get("confidence", {}))
        answers: dict[str, bool] = result.output.model_dump()
        return {
            f"Jev_{question}": EvaluationReason(
                answer, f"confidence {confidence.get(question, float('nan')):.2f}"
            )
            for question, answer in answers.items()
        }


# ── Deterministic, reference-based (need the golden answer) ──


def golden(ctx: Ctx) -> MeetingTodos:
    assert ctx.expected_output is not None, "every case has an expected output"
    return ctx.expected_output


@dataclass
class MeetingDateCorrect(TodoEvaluator):
    @override
    def evaluate(self, ctx: Ctx) -> EvaluationReason:
        expected, actual = golden(ctx).meeting_date, ctx.output.meeting_date
        return EvaluationReason(
            actual == expected, f"expected {expected}, got {actual}"
        )


@dataclass
class AttendeesMatch(TodoEvaluator):
    @override
    def evaluate(self, ctx: Ctx) -> EvaluationReason:
        expected = {a.lower() for a in golden(ctx).attendees}
        actual = {a.lower() for a in ctx.output.attendees}
        return EvaluationReason(
            actual == expected,
            f"missing {sorted(expected - actual)}, extra {sorted(actual - expected)}",
        )


@dataclass
class TodoCount(TodoEvaluator):
    @override
    def evaluate(self, ctx: Ctx) -> EvaluationReason:
        expected, actual = len(golden(ctx).todos), len(ctx.output.todos)
        return EvaluationReason(
            actual == expected, f"expected {expected} todos, got {actual}"
        )


@dataclass
class OwnerRecall(TodoEvaluator):
    """Score: fraction of expected (who, when) pairs found in the output."""

    @override
    def evaluate(self, ctx: Ctx) -> EvaluationReason:
        remaining = [(t.who.lower(), t.when) for t in ctx.output.todos]
        missed: list[str] = []
        for t in golden(ctx).todos:
            key = (t.who.lower(), t.when)
            if key in remaining:
                remaining.remove(key)
            else:
                missed.append(f"{t.who} by {t.when}: {t.what}")
        score = 1 - len(missed) / len(golden(ctx).todos)
        return EvaluationReason(
            round(score, 2), f"missed {missed}" if missed else "all found"
        )


# ── Online: everything that doesn't need a golden answer also runs on every real run ──
quality_judge = LLMJudge(
    model=JUDGE_MODEL,
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
        OnlineEvaluator(evaluator=e, sample_rate=0.1) if e is quality_judge else e
        for e in ONLINE_EVALUATORS
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
            model=JUDGE_MODEL,
            rubric="The output covers every action item in the expected output and invents none.",
            include_input=True,
            include_expected_output=True,
        ),
        # Operational: latency and cost (retries from guardrails show up here).
        MaxDuration(seconds=90),
        MaxModelRequests(max_requests=3),
    ],
)

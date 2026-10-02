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
  1. The system under test      — extraction agent + lexguard guardrails (output models in models.py)
     The golden dataset + evals — evals.py: schema → deterministic → lexguard → reference → LLM judge → operational
  2. The improver                — prompt rewrite + capability creation
  3. The loop                    — eval → improve → re-eval, then diff against the baseline
"""

import asyncio
import shutil
import sys
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from lexguard import Injection
from lexguard.integrations.guardrails.pydantic_ai import lexguard_guard
from pydantic_ai_harness.capability_creation import CapabilityCreation
from pydantic_ai_harness.guardrails import (
    GuardrailResult,
    InputBlocked,
    InputGuardrail,
    OutputGuardrail,
)
from pydantic_evals.reporting import EvaluationReport

from oreilly_edd_course.evals import NEVER_IN_OUTPUT, dataset, online_evals
from oreilly_edd_course.models import MeetingTodos
from oreilly_edd_course.telemetry import init_telemetry

MODEL = "google:gemini-3.8-flash"

HERE = Path(__file__).parent
MAX_ITERATIONS = 3

# What gets improved — committed to git, so every improvement is a reviewable diff.
INSTRUCTIONS_PATH = HERE / "instructions.md"
CAPABILITIES_DIR = HERE / "capabilities"

# Deliberately naive starting point (`--fresh` resets to it) — the evals will tell us what's missing.
BASELINE_INSTRUCTIONS = "Extract the action items from this meeting transcript."


# ═══ 1. The system under test ══════════════════════════════════════════════
# The output models are in models.py; the golden dataset and evals are in evals.py.


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

# Authored capabilities (by the improver or the extractor itself) live here. `store.load_active()` imports
# every active one so we can thread it into the next run.
capability_authoring = CapabilityCreation(directory=CAPABILITIES_DIR)

# The agent under test can author capabilities too: whatever it writes is live on its next run.
extractor_agent = Agent(
    MODEL,
    output_type=MeetingTodos,
    retries=4,
    capabilities=[*GUARDRAILS, capability_authoring],
)


async def extract_todos(transcript: str) -> MeetingTodos:
    result = await extractor_agent.run(
        transcript,
        instructions=INSTRUCTIONS_PATH.read_text(),
        capabilities=[online_evals, *capability_authoring.store.load_active()],
    )
    return result.output


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


# ═══ 2. The improver ═══════════════════════════════════════════════════════
# An agent reads the eval failures and pulls two levers: rewrite the prompt, or author
# capabilities (tools, guardrails, hooks). It also reviews what the extractor wrote for itself.


class PromptChange(BaseModel):
    instructions: str = Field(description="The full, updated extraction instructions")
    reason: str = Field(
        description="What you changed and why, including any capability you authored"
    )


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

improver = Agent(
    MODEL,
    output_type=PromptChange,
    instructions=IMPROVER_INSTRUCTIONS,
    capabilities=[capability_authoring],
)


async def improve(failures: list[str]) -> PromptChange:
    instructions, capabilities = await asyncio.gather(
        asyncio.to_thread(INSTRUCTIONS_PATH.read_text),
        asyncio.to_thread(capability_authoring.store.list_all),
    )
    active = [c.name for c in capabilities if c.status == "active" and not c.last_error]
    failure_list = "\n".join(f"- {f}" for f in failures)
    prompt = f"""\
Current instructions:
{instructions}

Active capabilities: 
{active or "none"}

Eval failures:
{failure_list}"""
    return (await improver.run(prompt)).output


# ═══ 3. The loop ═══════════════════════════════════════════════════════════


def reset() -> None:
    """Back to the naive prompt with no authored capabilities (`--fresh`)."""
    shutil.rmtree(CAPABILITIES_DIR, ignore_errors=True)
    _ = INSTRUCTIONS_PATH.write_text(BASELINE_INSTRUCTIONS)


async def evaluate(label: str) -> EvaluationReport:
    report = await dataset.evaluate(extract_todos, name=label)
    report.print(include_reasons=True, include_input=True, include_output=True)
    return report


async def main(fresh: bool = False) -> None:
    # 1. Async check & reset
    exists = await asyncio.to_thread(INSTRUCTIONS_PATH.exists)
    if fresh or not exists:
        await asyncio.to_thread(reset)

    baseline = await evaluate("baseline")
    report = baseline

    for iteration in range(1, MAX_ITERATIONS + 1):
        # 2. If summarise_failures is heavy, offload it; otherwise keep inline
        failures = summarise_failures(report)
        if not failures:
            print("\nAll evals pass.")
            break

        print(
            f"\n── Improving ({iteration}/{MAX_ITERATIONS}): {len(failures)} failure(s) ──"
        )
        change = await improve(failures)

        # 3. Offload file writing
        _ = await asyncio.to_thread(INSTRUCTIONS_PATH.write_text, change.instructions)
        print(f"Reason: {change.reason}")

        # 4. Offload store listing
        caps = await asyncio.to_thread(capability_authoring.store.list_all)
        for cap in caps:
            err = f" ERROR: {cap.last_error}" if cap.last_error else ""
            print(f"  capability {cap.name} [{cap.status}]{err}")

        report = await evaluate(f"iteration {iteration}")

    print("\n══ Baseline → final ══")
    report.print(baseline=baseline)
    print(f"\nReview what changed: git diff {HERE.relative_to(Path.cwd())}")
    print("Commit to keep the improvements, or `git checkout` to throw them away.")


if __name__ == "__main__":
    init_telemetry(service_name="meeting-todos")
    asyncio.run(main(fresh="--fresh" in sys.argv))

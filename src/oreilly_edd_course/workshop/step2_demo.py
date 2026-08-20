"""
Step 2: The Full EDD Loop — DEMO.

A single, run-it-and-watch showcase that ties the whole eval-driven-development
story together on the meeting-todo extractor from Step 1:

  ACT 1  Comprehensive evaluation — structural (count, no-dupes) + semantic
         (LLMJudge) + lexical: a lexguard lexicon that scores each todo's
         wording for vague/weak phrasing.
  ACT 2  Self-improvement — run evals, collect failures, and let an improver
         agent rewrite the extraction INSTRUCTIONS to fix them. The agent also
         *proposes* new vague phrasings it spots; those are surfaced as
         paste-able code for a human to review and promote — never silently
         written back.
  ACT 3  Production monitoring — simulate live traffic, run the cheap
         deterministic lexicon guard on 100% of it and a sampled LLMJudge,
         log to JSONL, and check for drift.

A note on philosophy (the point of this demo): the *instructions* are runtime
state the loop is allowed to optimize. The *lexicon* is a policy/judgment
artifact — what counts as "vague" — so it lives in CODE (below), reviewed,
diffed, and versioned like the evals themselves. The agent can suggest additions,
but a human promotes them by editing the code, not by mutating a data file.

    uv run src/oreilly_edd_course/workshop/step2_demo.py
"""

import asyncio
import random
from collections.abc import Iterable
from datetime import date, datetime
from pathlib import Path

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import EvaluatorContext, LLMJudge

from lexguard import Lexicon

from oreilly_edd_course.providers import get_model
from oreilly_edd_course.telemetry import init_telemetry
from oreilly_edd_course.workshop.step1_evals_solution import (
    MeetingTodos,
    NoDuplicateTodos,
    Todo,
    TodoCount,
    t1,
    t2,
    t3,
)

model = get_model()

WORKSHOP = Path(__file__).parent
INSTRUCTIONS_PATH = WORKSHOP / "improver_instructions.md"
PROD_LOG_PATH = Path("prod_evals_log.jsonl")

RUBRIC = (
    "- TODOs should be clear, concise, and actionable.\n"
    "- No hallucinated goals.\n"
    "- Each TODO should name a responsible person and a real due date."
)

# Deliberately weak starting point so the improvement loop has room to work.
SEED_INSTRUCTIONS = "Extract todos from the transcript as a MeetingTodos object."


# ── The custom lexicon lives in CODE — this is the source of truth ───────────
#
# A domain guardrail for weak/vague todo phrasing, spelled out in full as a
# plain `Lexicon` literal — no runtime `.extend()` composition. The entire policy
# is visible here: to change what counts as vague, edit this list and send a PR,
# reviewed and versioned exactly like the evaluators. Because the whole set is
# authored (not inherited), *removing* a term is just deleting a line — there is
# no separate "subtract from the base" problem. The improver agent may *propose*
# additions at runtime; they are printed as paste-able code for a human to
# promote here, not written back automatically.

VAGUE_TODO = Lexicon(
    "vague_todo",
    indicates=[
        "a few",
        "anything",
        "asap-ish",
        "at some point",
        "bits",
        "circle back",
        "deal with",
        "follow up on",
        "handle it",
        "kind of",
        "look into",
        "some",
        "something",
        "sometime soon",
        "sort of",
        "sort out",
        "stuff",
        "that thing",
        "the usual",
        "things",
        "whatever",
        "when we get a chance",
        "you know",
    ],
    fix="resolve the referent from context or ask one clarifying question",
)


# ── Runtime state: only the instructions are optimized by the loop ───────────


def get_instructions() -> str:
    return INSTRUCTIONS_PATH.read_text().strip()


def save_instructions(instructions: str) -> None:
    INSTRUCTIONS_PATH.write_text(instructions)


def reset_instructions() -> None:
    """Reset to the seed so the demo is reproducible."""
    save_instructions(SEED_INSTRUCTIONS)


# ── The agent under evaluation (dynamic instructions) ────────────────────────


async def extract_todos(transcript: str) -> MeetingTodos:
    """Same extractor as Step 1, but reads its instructions from disk so the
    improvement loop can rewrite them between iterations."""
    agent = Agent(
        model=model,
        output_type=MeetingTodos,
        retries=4,
        instructions=get_instructions(),
    )
    return (await agent.run(transcript)).output


# ── Comprehensive evaluation dataset ─────────────────────────────────────────

EXPECTED = {
    "standup_meeting": MeetingTodos(
        todos=[
            Todo(who="Alex Kim", what="Send Redis cluster details to Marcus Rodriguez", when=date(2026, 1, 9), criticality="high"),
            Todo(who="Alex Kim", what="Send connection pooling config to Marcus Rodriguez", when=date(2026, 1, 9), criticality="high"),
            Todo(who="Sarah Chen", what="Ping design team about mockups", when=date(2026, 1, 9), criticality="medium"),
            Todo(who="Marcus Rodriguez", what="Review Priya's PR #847 by end of day", when=date(2026, 1, 9), criticality="high"),
            Todo(who="Sarah Chen", what="Confirm Wednesday afternoon works for DB migration with Product", when=date(2026, 1, 10), criticality="medium"),
            Todo(who="Alex Kim", what="Schedule maintenance window for database migration", when=date(2026, 1, 9), criticality="medium"),
            Todo(who="Priya Patel", what="Create ticket for updating testing documentation", when=date(2026, 1, 9), criticality="low"),
        ],
        meeting_date=date(2026, 1, 9),
        attendees=["Sarah Chen", "Marcus Rodriguez", "Alex Kim", "Priya Patel"],
    ),
    "product_planning": MeetingTodos(
        todos=[
            Todo(who="Kevin Martinez", what="Research data warehouse options with cost estimates and migration timeline", when=date(2026, 1, 16), criticality="high"),
            Todo(who="Tom Richardson", what="Sync with Kevin mid-week on technical integration points", when=date(2026, 1, 14), criticality="medium"),
            Todo(who="Maya Johnson", what="Set up requirements calls with 3 enterprise customers", when=date(2026, 1, 14), criticality="high"),
            Todo(who="Maya Johnson", what="Line up 2-3 customers for user testing session", when=date(2026, 1, 14), criticality="medium"),
        ],
        meeting_date=date(2026, 1, 9),
        attendees=["Jennifer Walsh", "Maya Johnson", "Tom Richardson", "Kevin Martinez", "Lisa Anderson"],
    ),
    "client_onboarding": MeetingTodos(
        todos=[
            Todo(who="Robert Park", what="Get Okta attribute schema from security team", when=date(2026, 1, 10), criticality="high"),
            Todo(who="Amanda Chen", what="Talk to marketing team about using their project as test case", when=date(2026, 1, 10), criticality="medium"),
            Todo(who="Amanda Chen", what="Request Jira admin access for Robert Park", when=date(2026, 1, 10), criticality="high"),
            Todo(who="Amanda Chen", what="Audit custom Jira fields and document what they're used for", when=date(2026, 1, 17), criticality="high"),
        ],
        meeting_date=date(2026, 1, 9),
        attendees=["Rachel Foster", "Amanda Chen", "Robert Park", "David Park"],
    ),
}

TRANSCRIPTS = {"standup_meeting": t1, "product_planning": t2, "client_onboarding": t3}


def build_dataset() -> Dataset[str, MeetingTodos, MeetingTodos]:
    """Comprehensive suite: structural per case, plus the lexical guard and a
    semantic LLMJudge across the dataset.

    The lexical check uses lexguard's own field selector — `field="todos[].what"`
    scores every todo's `what` in one pass, with span-level diagnostics.
    """
    cases = [
        Case(
            name=name,
            inputs=TRANSCRIPTS[name],
            expected_output=expected,
            evaluators=(TodoCount(expected_count=len(expected.todos)),),
        )
        for name, expected in EXPECTED.items()
    ]
    return Dataset[str, MeetingTodos, MeetingTodos](
        cases=cases,
        evaluators=[
            LLMJudge(model=model, rubric=RUBRIC),
            NoDuplicateTodos(),
            VAGUE_TODO.absent(field="todos[].what"),
        ],
    )


def collect_failures(report) -> list[str]:
    """Gather failing evaluators across the report.

    pydantic-evals routes results by value type: boolean evaluators (LLMJudge's
    pass/fail, the lexicon guard) land in `case.assertions`, while numeric ones
    (our 0.0/1.0 structural checks) land in `case.scores`. Read both.
    """
    failures: list[str] = []
    for c in report.cases:
        for key, r in c.assertions.items():
            if not r.value:
                failures.append(f"Case '{c.name}' [{key}]: {r.reason or 'assertion failed'}")
        for key, r in c.scores.items():
            if r.value == 0:
                failures.append(f"Case '{c.name}' [{key}]: {r.reason or 'scored 0'}")
    return failures


# ── ACT 2: the improver (rewrites instructions, PROPOSES lexicon terms) ───────


class Improvement(BaseModel):
    instructions: str
    proposed_vague_terms: list[str]
    reason: str


async def improve(failures: list[str]) -> Improvement:
    agent = Agent(
        model=model,
        output_type=Improvement,
        instructions=(
            "You tune a meeting-todo extraction agent that is failing evals.\n"
            "1. Rewrite `instructions` to fix the failures with the minimum "
            "necessary changes. Output must stay valid MeetingTodos JSON with "
            "who/what/when/criticality per todo.\n"
            "2. In `proposed_vague_terms`, list any vague or weak phrasings you "
            "see in the failing outputs that a guardrail should catch in future "
            "(short lowercase phrases, e.g. 'circle back'). These are proposals a "
            "human will review — return [] if none."
        ),
    )
    prompt = (
        f"Current instructions:\n{get_instructions()}\n\n"
        f"Failures:\n" + "\n".join(failures)
    )
    return (await agent.run(prompt)).output


async def run_improvement_loop(max_iterations: int = 5) -> set[str]:
    """Optimize the instructions against the fixed code lexicon. Returns the set
    of new vague terms the agent proposed along the way (for human review)."""
    dataset = build_dataset()
    proposed: set[str] = set()
    existing = set(VAGUE_TODO.indicates)

    for iteration in range(1, max_iterations + 1):
        print(f"\n─── Iteration {iteration} ───")
        print(f"  Instructions: {get_instructions()[:70]}...")

        report = await dataset.evaluate(extract_todos)
        report.print(include_input=False, include_output=False, include_reasons=True)

        failures = collect_failures(report)
        if not failures:
            print("\n  ✅ All evaluators pass — extraction is solid.")
            break

        print(f"\n  {len(failures)} failure(s); asking the improver to fix them...")
        improvement = await improve(failures)
        save_instructions(improvement.instructions)

        new = {t.lower() for t in improvement.proposed_vague_terms} - existing - proposed
        if new:
            proposed |= new
            print(f"  Agent proposes {len(new)} lexicon term(s) for review: {sorted(new)}")
        print(f"  Reason: {improvement.reason}")
    else:
        print("\n  Max iterations reached.")

    return proposed


# ── Promote-to-code: emit the reviewed lexicon as paste-able source ──────────


def propose_lexicon_code(lexicon: Lexicon, proposed: Iterable[str]) -> str:
    """Emit a paste-able full `Lexicon(...)` definition, sorted and quoted, with
    the agent's candidate terms flagged. A human reviews this and pastes the
    accepted result over the `VAGUE_TODO` definition above — the lexicon stays a
    self-contained code literal, never a data file.

    (This is a local stand-in for a future `lexguard` `Lexicon.as_code()`.)
    """
    proposed = set(proposed)
    terms = sorted(set(lexicon.indicates) | proposed)
    lines = "\n".join(
        f"        {t!r},  # ← proposed, review me" if t in proposed else f"        {t!r},"
        for t in terms
    )
    return (
        f"VAGUE_TODO = Lexicon(\n    {lexicon.name!r},\n    indicates=[\n"
        + lines
        + f"\n    ],\n    fix={lexicon.fix!r},\n)"
    )


# ── ACT 3: production monitoring ─────────────────────────────────────────────


class ProductionEvalResult(BaseModel):
    timestamp: datetime
    transcript_preview: str
    num_todos: int
    lexicon_score: float  # deterministic guard, computed on 100% of traffic
    judge_score: float | None  # LLMJudge, only on sampled requests
    reason: str


class ProductionMonitor:
    """Cheap deterministic lexicon guard on every request; expensive LLMJudge on
    a sample. Logs both for trend analysis and drift detection."""

    def __init__(self, sample_rate: float = 0.5, log_path: Path = PROD_LOG_PATH):
        assert 0 < sample_rate <= 1.0
        self.sample_rate = sample_rate
        self.log_path = log_path
        self.judge = LLMJudge(model=model, rubric=RUBRIC)

    def _lexicon_score(self, output: MeetingTodos) -> float:
        # Per-todo fraction clean. (lexguard's evaluator gives one collection-level
        # verdict; a per-item score is still hand-rolled — a candidate lexguard feature.)
        if not output.todos:
            return 1.0
        clean = sum(1 for todo in output.todos if not VAGUE_TODO.fires(todo.what))
        return clean / len(output.todos)

    async def evaluate_output(self, transcript: str, output: MeetingTodos) -> ProductionEvalResult:
        lexicon_score = self._lexicon_score(output)

        judge_score: float | None = None
        reason = "lexicon guard only (not sampled for LLMJudge)"
        if random.random() <= self.sample_rate:
            ctx = EvaluatorContext[str, MeetingTodos, dict](
                name="production_eval",
                inputs=transcript,
                output=output,
                expected_output=None,
                metadata={},
                duration=0.0,
                _span_tree=None,
                attributes={},
                metrics={},
            )
            result = await self.judge.evaluate(ctx)
            if isinstance(result, dict):
                key = next(iter(result))
                judge_score, reason = float(result[key].value), str(result[key].reason)
            else:
                judge_score, reason = float(result.value), str(result.reason)

        entry = ProductionEvalResult(
            timestamp=datetime.now(),
            transcript_preview=transcript[:80],
            num_todos=len(output.todos),
            lexicon_score=round(lexicon_score, 3),
            judge_score=judge_score,
            reason=reason,
        )
        with open(self.log_path, "a") as f:
            f.write(entry.model_dump_json() + "\n")
        return entry

    def reset_log(self) -> None:
        """Start each demo run from an empty log so drift detection is reproducible."""
        self.log_path.write_text("")

    def load_history(self) -> list[ProductionEvalResult]:
        if not self.log_path.exists():
            return []
        history: list[ProductionEvalResult] = []
        for line in self.log_path.read_text().splitlines():
            if not line.strip():
                continue
            try:
                history.append(ProductionEvalResult.model_validate_json(line))
            except ValueError:
                continue  # skip lines from an older schema
        return history

    def detect_drift(self, window: int = 3) -> None:
        scores = [r.lexicon_score for r in self.load_history()]
        if len(scores) < window * 2:
            print(f"  Not enough history for drift ({len(scores)} points)")
            return
        recent = sum(scores[-window:]) / window
        baseline = sum(scores[:-window]) / len(scores[:-window])
        drop = baseline - recent
        if drop > 0.2:
            print(f"  ⚠️  DRIFT: guard {baseline:.2f} → {recent:.2f} (drop {drop:.2f})")
        else:
            print(f"  ✅ No drift: guard {baseline:.2f} → {recent:.2f}")


async def run_production_monitoring(num_requests: int = 6) -> None:
    monitor = ProductionMonitor(sample_rate=0.5)
    monitor.reset_log()
    print(f"Simulating {num_requests} production requests "
          f"(lexicon guard on all, LLMJudge on ~{int(monitor.sample_rate * 100)}%)...\n")
    for i in range(num_requests):
        name = random.choice(list(TRANSCRIPTS))
        output = await extract_todos(TRANSCRIPTS[name])
        r = await monitor.evaluate_output(TRANSCRIPTS[name], output)
        judge = f"{r.judge_score:.2f}" if r.judge_score is not None else "—"
        print(f"  [{i + 1}] {name:18} guard={r.lexicon_score:.2f} judge={judge}")

    print(f"\nLogged to {monitor.log_path}")
    monitor.detect_drift()


# ── Orchestration ────────────────────────────────────────────────────────────


async def main() -> None:
    reset_instructions()

    print("=" * 70)
    print("ACT 1 & 2 — COMPREHENSIVE EVALS + SELF-IMPROVEMENT")
    print("=" * 70)
    proposed = await run_improvement_loop()

    print("\n" + "=" * 70)
    print("PROMOTE TO CODE — review the agent's proposed lexicon terms")
    print("=" * 70)
    if proposed:
        print("The agent proposed new vague phrasings. Review and paste the accepted")
        print("result over the VAGUE_TODO definition in this file (it stays code):\n")
        print(propose_lexicon_code(VAGUE_TODO, proposed))
    else:
        print("No new lexicon terms proposed — the code lexicon already covers it.")

    print("\n" + "=" * 70)
    print("ACT 3 — PRODUCTION MONITORING")
    print("=" * 70)
    await run_production_monitoring()

    print("\n" + "=" * 70)
    print(f"Final instructions:\n  {get_instructions()}")
    print("=" * 70)


if __name__ == "__main__":
    init_telemetry(project_name="edd-workshop")
    asyncio.run(main())

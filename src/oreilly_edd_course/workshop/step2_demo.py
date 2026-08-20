"""
Step 2: The Full EDD Loop — DEMO.

A single, run-it-and-watch showcase that ties the whole eval-driven-development
story together on the meeting-todo extractor from Step 1:

  ACT 1  Comprehensive evaluation — structural + semantic (LLMJudge) + lexical
         (a lexguard lexicon that scores each todo for vague/weak phrasing).
  ACT 2  Self-improvement — run evals, collect failures, and let an improver
         agent rewrite the extraction instructions AND grow a custom lexguard
         lexicon of vague phrasings it spots. The guardrail co-evolves with the
         agent: instructions get sharper, the lexicon gets more comprehensive.
  ACT 3  Production monitoring — simulate live traffic, run the cheap
         deterministic lexicon guard on 100% of it and a sampled LLMJudge,
         log to JSONL, and check for drift.

Models and structural evaluators are imported from Step 1 — this demo layers
evaluation, improvement, and monitoring on top of them.

    uv run src/oreilly_edd_course/workshop/step2_demo.py
"""

import asyncio
import json
import random
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import (
    EvaluationReason,
    Evaluator,
    EvaluatorContext,
    LLMJudge,
)
from typing_extensions import override

from lexguard import Vague

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
VAGUE_TERMS_PATH = WORKSHOP / "custom_vague_terms.json"
PROD_LOG_PATH = Path("prod_evals_log.jsonl")

RUBRIC = (
    "- TODOs should be clear, concise, and actionable.\n"
    "- No hallucinated goals.\n"
    "- Each TODO should name a responsible person and a real due date."
)

# Deliberately weak starting point so the improvement loop has room to work.
SEED_INSTRUCTIONS = "Extract todos from the transcript as a MeetingTodos object."

# Seed vocabulary for the custom "vague todo" lexicon. The improver agent grows
# this list from phrasings it sees in failing outputs.
SEED_VAGUE_TERMS = [
    "at some point",
    "when we get a chance",
    "circle back",
    "look into",
    "follow up on",
    "sort out",
    "deal with",
    "handle it",
    "sometime soon",
    "asap-ish",
]


# ── Persisted, co-evolving state ─────────────────────────────────────────────


def get_instructions() -> str:
    return INSTRUCTIONS_PATH.read_text().strip()


def save_instructions(instructions: str) -> None:
    INSTRUCTIONS_PATH.write_text(instructions)


def get_vague_terms() -> list[str]:
    return json.loads(VAGUE_TERMS_PATH.read_text())


def save_vague_terms(terms: list[str]) -> None:
    VAGUE_TERMS_PATH.write_text(json.dumps(terms, indent=2) + "\n")


def load_lexicon():
    """Build the current 'vague todo' lexicon: lexguard's built-in Vague
    coverage extended with the terms the agent has curated so far."""
    return Vague.extend(indicates=get_vague_terms())


def reset_state() -> None:
    """Reset instructions + lexicon to their seeds so the demo is reproducible."""
    save_instructions(SEED_INSTRUCTIONS)
    save_vague_terms(SEED_VAGUE_TERMS)


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


# ── ACT 1: the lexical evaluator (lexguard) ──────────────────────────────────


@dataclass
class TodoVagueness(Evaluator):
    """Score each todo's `what` against the current vague-phrasing lexicon.

    Deterministic and free — no model call. Fails (0.0) if any todo uses vague
    or weak wording, and reports exactly which terms fired so the improver can
    act on them.
    """

    @override
    async def evaluate(
        self, ctx: EvaluatorContext[str, MeetingTodos]
    ) -> EvaluationReason:
        lexicon = load_lexicon()
        offenders: list[str] = []
        for todo in ctx.output.todos:
            if lexicon.fires(todo.what):
                hits = ", ".join(sorted(lexicon.hits(todo.what)))
                offenders.append(f"{todo.who}: '{todo.what}' [{hits}]")

        if offenders:
            return EvaluationReason(
                value=0.0,
                reason=f"{len(offenders)} vague todo(s) — " + "; ".join(offenders),
            )
        return EvaluationReason(
            value=1.0, reason=f"No vague phrasing across {len(ctx.output.todos)} todos"
        )


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
    """Comprehensive suite: structural (count, no-dupes) + lexical (vagueness)
    per case, plus a semantic LLMJudge across the dataset."""
    cases = [
        Case(
            name=name,
            inputs=TRANSCRIPTS[name],
            expected_output=expected,
            evaluators=(
                TodoCount(expected_count=len(expected.todos)),
                NoDuplicateTodos(),
                TodoVagueness(),
            ),
        )
        for name, expected in EXPECTED.items()
    ]
    return Dataset[str, MeetingTodos, MeetingTodos](
        cases=cases,
        evaluators=[LLMJudge(model=model, rubric=RUBRIC)],
    )


def collect_failures(report) -> list[str]:
    """Gather failing evaluators across the report.

    pydantic-evals routes results by value type: boolean evaluators (LLMJudge's
    pass/fail) land in `case.assertions`, while numeric ones (our 0.0/1.0
    structural + lexical checks) land in `case.scores`. Read both.
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


# ── ACT 2: the improver (rewrites instructions AND grows the lexicon) ─────────


class Improvement(BaseModel):
    instructions: str
    new_vague_terms: list[str]
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
            "2. In `new_vague_terms`, list any vague or weak phrasings you see in "
            "the failing outputs that a guardrail should catch in future (short "
            "lowercase phrases, e.g. 'circle back'). Return [] if none."
        ),
    )
    prompt = (
        f"Current instructions:\n{get_instructions()}\n\n"
        f"Current vague-phrase lexicon terms:\n{get_vague_terms()}\n\n"
        f"Failures:\n" + "\n".join(failures)
    )
    return (await agent.run(prompt)).output


async def run_improvement_loop(max_iterations: int = 5) -> None:
    dataset = build_dataset()
    for iteration in range(1, max_iterations + 1):
        print(f"\n─── Iteration {iteration} ───")
        print(f"  Instructions: {get_instructions()[:70]}...")
        print(f"  Lexicon terms: {len(get_vague_terms())}")

        report = await dataset.evaluate(extract_todos)
        report.print(include_input=False, include_output=False, include_reasons=True)

        failures = collect_failures(report)
        if not failures:
            print("\n  ✅ All evaluators pass — extraction is solid.")
            return

        print(f"\n  {len(failures)} failure(s); asking the improver to fix them...")
        improvement = await improve(failures)

        save_instructions(improvement.instructions)
        added = [t for t in improvement.new_vague_terms if t not in get_vague_terms()]
        if added:
            save_vague_terms(get_vague_terms() + added)
            print(f"  + Grew lexicon by {len(added)}: {added}")
        print(f"  Reason: {improvement.reason}")

    print("\n  Max iterations reached.")


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
        lexicon = load_lexicon()
        if not output.todos:
            return 1.0
        clean = sum(1 for todo in output.todos if not lexicon.fires(todo.what))
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
    reset_state()

    print("=" * 70)
    print("ACT 1 & 2 — COMPREHENSIVE EVALS + SELF-IMPROVEMENT")
    print("=" * 70)
    await run_improvement_loop()

    print("\n" + "=" * 70)
    print("ACT 3 — PRODUCTION MONITORING")
    print("=" * 70)
    await run_production_monitoring()

    print("\n" + "=" * 70)
    print(f"Final instructions:\n  {get_instructions()}")
    print(f"Final lexicon terms ({len(get_vague_terms())}): {get_vague_terms()}")
    print("=" * 70)


if __name__ == "__main__":
    init_telemetry(project_name="edd-workshop")
    asyncio.run(main())

"""
Step 3: Evals in Production — SOLUTION.

Production evals monitor live agent outputs: tracking quality over time,
detecting drift, and alerting on degradation — using LLMJudge on real traffic.
"""

import asyncio
import json
import random
from datetime import date, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_evals.evaluators import EvaluatorContext, LLMJudge

model = OpenAIChatModel("qwen/qwen3.6-35b-a3b@q4_k_m", provider=OpenAIProvider(base_url="http://localhost:1234/v1", api_key="lm-studio"))


class Todo(BaseModel):
    who: str
    what: str
    when: date
    criticality: Literal["high", "medium", "low"]
    theme: Literal["Coordination Task", "Code Review", "Other"]


class MeetingTodos(BaseModel):
    todos: list[Todo]
    meeting_date: date
    attendees: list[str]


async def extract_todos(transcript: str) -> MeetingTodos:
    agent = Agent(model=model, output_type=MeetingTodos, retries=4, instructions="Extract ALL todos.")
    return (await agent.run(transcript)).output


def load_transcript(path: str) -> str:
    with open(path) as f:
        return f.read()


PRODUCTION_TRANSCRIPTS = [load_transcript(f"src/oreilly_edd_course/transcript{i}.txt") for i in range(1, 4)]


class ProductionEvalResult(BaseModel):
    timestamp: datetime
    transcript_preview: str
    score: float
    reason: str
    num_todos: int


class ProductionMonitor:
    """Monitors agent outputs in production by evaluating a sample of requests."""

    def __init__(self, sample_rate: float = 1.0, log_path: Path = Path("prod_evals_log.jsonl")):
        assert 0 < sample_rate <= 1.0
        self.sample_rate = sample_rate
        self.log_path = log_path
        self.judge = LLMJudge(model=model, rubric="- TODOs should be clear, concise, and actionable.\n- No hallucinated goals.")

    async def evaluate_production_output(self, transcript: str, output: MeetingTodos) -> ProductionEvalResult | None:
        """Evaluate a single production output using LLMJudge. Returns None if not sampled."""
        if random.random() > self.sample_rate:
            return None

        # Run LLMJudge on the production output
        ctx = EvaluatorContext[str, MeetingTodos](inputs=transcript, output=output, expected_output=None, metadata={})
        eval_result = await self.judge.evaluate(ctx)

        result = ProductionEvalResult(
            timestamp=datetime.now(),
            transcript_preview=transcript[:100],
            score=eval_result.value,
            reason=eval_result.reason,
            num_todos=len(output.todos),
        )

        with open(self.log_path, "a") as f:
            f.write(result.model_dump_json() + "\n")

        return result

    def load_history(self) -> list[ProductionEvalResult]:
        if not self.log_path.exists():
            return []
        results = []
        with open(self.log_path) as f:
            for line in f:
                if line.strip():
                    results.append(ProductionEvalResult.model_validate_json(line))
        return results

    def detect_drift(self, window: int = 10) -> bool:
        """Detect if recent scores are trending down compared to historical average."""
        history = self.load_history()
        if len(history) < window * 2:
            print(f"  Not enough data for drift detection ({len(history)} points, need {window * 2})")
            return False

        recent = [r.score for r in history[-window:]]
        baseline = [r.score for r in history[:-window]]
        recent_avg = sum(recent) / len(recent)
        baseline_avg = sum(baseline) / len(baseline)
        drop = baseline_avg - recent_avg

        if drop > 0.2:
            print(f"  ⚠️ DRIFT: baseline {baseline_avg:.2f} → recent {recent_avg:.2f} (drop of {drop:.2f})")
            return True
        print(f"  ✅ No drift: baseline {baseline_avg:.2f} → recent {recent_avg:.2f}")
        return False

    def summary_report(self) -> dict:
        """Generate a summary report of all production eval results."""
        history = self.load_history()
        if not history:
            return {"total": 0, "average_score": 0, "message": "No data"}

        scores = [r.score for r in history]
        return {
            "total_evaluations": len(history),
            "average_score": round(sum(scores) / len(scores), 3),
            "min_score": round(min(scores), 3),
            "max_score": round(max(scores), 3),
            "recent_drift": self.detect_drift(window=3),
        }


async def simulate_production_traffic(monitor: ProductionMonitor, num_requests: int = 10):
    """Simulate production traffic by processing random transcripts."""
    print(f"Simulating {num_requests} production requests...\n")
    for i in range(num_requests):
        transcript = random.choice(PRODUCTION_TRANSCRIPTS)
        output = await extract_todos(transcript)
        result = await monitor.evaluate_production_output(transcript, output)
        if result:
            print(f"  [{i+1}] Score: {result.score:.2f} — {result.reason[:60]}")
    print(f"\nLogged to {monitor.log_path}")


async def main():
    monitor = ProductionMonitor(sample_rate=1.0)
    await simulate_production_traffic(monitor, num_requests=6)

    print("\n" + "=" * 60)
    print("PRODUCTION MONITORING REPORT")
    print("=" * 60)
    report = monitor.summary_report()
    for key, value in report.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    asyncio.run(main())
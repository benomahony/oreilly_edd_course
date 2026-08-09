"""
Step 3: Evals in Production — Exercise.

Production evals monitor live agent outputs, not just test datasets.
They track quality over time, detect drift, and alert on degradation.

Exercise: Fill in the TODOs to build a production monitoring system.
"""

import asyncio
import json
import random
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Literal

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_evals.evaluators import LLMJudge

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


# ── Simulated production data stream ──

def load_transcript(path: str) -> str:
    with open(path) as f:
        return f.read()


# In production, this would be a queue of real user transcripts
PRODUCTION_TRANSCRIPTS = [
    load_transcript(f"src/oreilly_edd_course/transcript{i}.txt")
    for i in range(1, 4)
]


# ── Production monitoring ──

class ProductionEvalResult(BaseModel):
    timestamp: datetime
    transcript_preview: str
    score: float
    reason: str
    num_todos: int


class ProductionMonitor:
    """Monitors agent outputs in production by evaluating every N-th request."""

    def __init__(self, sample_rate: float = 1.0, log_path: Path = Path("prod_evals_log.jsonl")):
        assert 0 < sample_rate <= 1.0, "Sample rate must be between 0 and 1"
        self.sample_rate = sample_rate
        self.log_path = log_path
        self.rubric = "- TODOs should be clear, concise, and actionable.\n- No hallucinated goals."
        self.judge = LLMJudge(model=model, rubric=self.rubric)

    async def evaluate_production_output(self, transcript: str, output: MeetingTodos) -> ProductionEvalResult | None:
        """Evaluate a single production output. Returns None if not sampled."""
        if random.random() > self.sample_rate:
            return None

        # TODO: Run the LLMJudge on this production output
        # Hint: LLMJudge.evaluate() takes an EvaluatorContext
        # You'll need to construct one with the transcript as input and MeetingTodos as output

        # For now, use a simple heuristic score
        score = min(1.0, len(output.todos) / 5.0)
        reason = f"Extracted {len(output.todos)} todos"

        result = ProductionEvalResult(
            timestamp=datetime.now(),
            transcript_preview=transcript[:100],
            score=score,
            reason=reason,
            num_todos=len(output.todos),
        )

        # Log to file
        with open(self.log_path, "a") as f:
            f.write(result.model_dump_json() + "\n")

        return result

    def load_history(self) -> list[ProductionEvalResult]:
        """Load all logged production eval results."""
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
            return False  # Not enough data

        recent = [r.score for r in history[-window:]]
        baseline = [r.score for r in history[:-window]]

        recent_avg = sum(recent) / len(recent)
        baseline_avg = sum(baseline) / len(baseline)

        drop = baseline_avg - recent_avg
        if drop > 0.2:
            print(f"  ⚠️ DRIFT DETECTED: baseline {baseline_avg:.2f} → recent {recent_avg:.2f} (drop of {drop:.2f})")
            return True

        print(f"  ✅ No drift: baseline {baseline_avg:.2f} → recent {recent_avg:.2f}")
        return False


# ── Simulate production traffic ──

async def simulate_production_traffic(monitor: ProductionMonitor, num_requests: int = 10):
    """Simulate production traffic by processing random transcripts."""
    print(f"Simulating {num_requests} production requests...\n")

    for i in range(num_requests):
        transcript = random.choice(PRODUCTION_TRANSCRIPTS)
        output = await extract_todos(transcript)

        result = await monitor.evaluate_production_output(transcript, output)
        if result:
            print(f"  [{i+1}] Score: {result.score:.2f} — {result.reason}")

    print(f"\nLogged to {monitor.log_path}")


# ── Main ──

async def main():
    monitor = ProductionMonitor(sample_rate=1.0)

    # Simulate production traffic
    await simulate_production_traffic(monitor, num_requests=6)

    # Check for drift
    print("\n" + "=" * 60)
    print("DRIFT DETECTION")
    print("=" * 60)
    monitor.detect_drift(window=3)

    # TODO: Print a summary report
    # - Total evaluations
    # - Average score
    # - Min/max scores
    # - Any drift alerts


if __name__ == "__main__":
    asyncio.run(main())
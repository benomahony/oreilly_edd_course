"""
Step 3: Evals in Production — SOLUTION.

A CI-friendly eval runner with threshold-based pass/fail,
regression detection against baselines, and JSON export.
"""

import asyncio
import json
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_evals import Case, Dataset
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


def load_transcript(path: str) -> str:
    with open(path) as f:
        return f.read()


t1 = load_transcript("src/oreilly_edd_course/workshop/transcript1.txt")
t2 = load_transcript("src/oreilly_edd_course/workshop/transcript2.txt")
t3 = load_transcript("src/oreilly_edd_course/workshop/transcript3.txt")


async def extract_todos(transcript: str) -> MeetingTodos:
    agent = Agent(model=model, output_type=MeetingTodos, retries=4, instructions="Extract ALL todos.")
    return (await agent.run(transcript)).output


dataset = Dataset(
    cases=[
        Case(name="Stand up", inputs=t1),
        Case(name="Product Planning", inputs=t2),
        Case(name="Client Onboarding", inputs=t3),
    ],
    evaluators=[LLMJudge(model=model, rubric="- TODOs should be clear, concise, and actionable.\n- No hallucinated goals.")],
)


def compute_scores(report) -> dict:
    results = []
    total, count = 0.0, 0
    for case in report.cases:
        vals = [r.value for r in case.assertions.values()]
        avg = sum(vals) / len(vals) if vals else 0
        total += sum(vals)
        count += len(vals)
        results.append({"name": case.name, "average_score": round(avg, 3), "passed": avg >= 0.5})
    return {"overall_score": round(total / count, 3) if count else 0, "cases": results,
            "passed_cases": sum(1 for r in results if r["passed"]), "failed_cases": sum(1 for r in results if not r["passed"])}


def check_regression(current: dict, baseline_path: Path | None) -> bool:
    if not baseline_path or not baseline_path.exists():
        return False
    baseline = json.loads(baseline_path.read_text())
    drop = baseline.get("scores", {}).get("overall_score", 0) - current.get("overall_score", 0)
    if drop > 0.05:
        print(f"  REGRESSION: score dropped by {drop:.3f}")
        return True
    return False


async def evaluate(output_dir: Path = Path("eval_reports"), threshold: float = 0.5, baseline_path: Path | None = None):
    output_dir.mkdir(parents=True, exist_ok=True)
    report = await dataset.evaluate(extract_todos)
    scores = compute_scores(report)

    # Export full report
    export = {
        "scores": scores,
        "threshold": threshold,
        "passed": scores["overall_score"] >= threshold,
        "cases_detail": [
            {
                "name": case.name,
                "input": case.inputs[:200] + ("..." if len(case.inputs) > 200 else ""),
                "output": str(case.output)[:500] if case.output else None,
                "assertions": {str(k): {"value": v.value, "reason": v.reason} for k, v in case.assertions.items()},
            }
            for case in report.cases
        ],
    }
    (output_dir / "eval_report.json").write_text(json.dumps(export, indent=2))
    print(f"  Report exported to {output_dir / 'eval_report.json'}")

    print(f"  Score: {scores['overall_score']:.3f} (threshold: {threshold})")
    print(f"  Cases: {scores['passed_cases']} passed / {scores['failed_cases']} failed")

    # Threshold check
    assert scores["overall_score"] >= threshold, f"Score {scores['overall_score']:.3f} below threshold {threshold}"

    # Regression check
    if check_regression(scores, baseline_path):
        assert False, "Regression detected — failing"

    # Save new baseline
    (output_dir / "baseline.json").write_text(json.dumps({"scores": scores}, indent=2))
    print("  Baseline saved")
    print("  ALL CHECKS PASSED")


if __name__ == "__main__":
    asyncio.run(evaluate())
"""
Step 1: Evals for the Action Extractor — Solution.

Demonstrates LLMJudge, EqualsExpected, and a custom NoDuplicateTodos evaluator.
"""

import asyncio
from dataclasses import dataclass
from datetime import date
from typing import Literal

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import (
    EqualsExpected,
    EvaluationReason,
    Evaluator,
    EvaluatorContext,
    LLMJudge,
)
from typing_extensions import override

model = OpenAIChatModel(
    "qwen/qwen3.6-35b-a3b@q4_k_m",
    provider=OpenAIProvider(base_url="http://localhost:1234/v1", api_key="lm-studio"),
)


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
    agent = Agent(
        model=model,
        output_type=MeetingTodos,
        retries=4,
        instructions="Extract ALL todos from the transcript as structured data.",
    )
    return (await agent.run(transcript)).output


# ── Custom evaluator: check for duplicate todos ──

@dataclass
class NoDuplicateTodos(Evaluator):
    @override
    async def evaluate(self, ctx: EvaluatorContext[str, MeetingTodos]) -> EvaluationReason:
        seen: set[tuple[str, str]] = set()
        for todo in ctx.output.todos:
            key = (todo.who.lower(), todo.what.lower())
            if key in seen:
                return EvaluationReason(value=0.0, reason=f"Duplicate: {todo.who} / {todo.what}")
            seen.add(key)
        return EvaluationReason(value=1.0, reason=f"No dupes in {len(ctx.output.todos)} todos")


# ── Dataset with multiple evaluator types ──

rubric = "- TODOs should be clear, concise, and actionable.\n- No hallucinated goals."

dataset = Dataset(
    cases=[
        Case(name="Stand up", inputs=t1, expected_output=7, evaluators=(EqualsExpected(),)),
        Case(name="Product Planning", inputs=t2),
        Case(name="Client Onboarding", inputs=t3),
    ],
    evaluators=[LLMJudge(model=model, rubric=rubric), NoDuplicateTodos()],
)


async def evaluate():
    report = await dataset.evaluate(extract_todos)
    report.print(include_input=True, include_output=True, include_reasons=True)

    passed = sum(1 for c in report.cases if all(r.value for r in c.assertions.values()))
    failed = len(report.cases) - passed
    print(f"\nSUMMARY: {passed} passed, {failed} failed")
    assert failed == 0, f"{failed} case(s) failed"


if __name__ == "__main__":
    asyncio.run(evaluate())
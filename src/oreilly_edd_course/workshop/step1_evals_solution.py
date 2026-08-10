"""
Step 1: Structured Extraction & Evals — Solution.

Pydantic models with validators, structured extraction, LLMJudge,
EqualsExpected, and a custom NoDuplicateTodos evaluator.
"""

import asyncio
from dataclasses import dataclass
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator
from pydantic_ai import Agent
from oreilly_edd_course.providers import get_model
from oreilly_edd_course.telemetry import init_telemetry
from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import (
    EqualsExpected,
    EvaluationReason,
    Evaluator,
    EvaluatorContext,
    LLMJudge,
)
from typing_extensions import override

model = get_model()


class Todo(BaseModel):
    who: str = Field(description="Person responsible", min_length=1)
    what: str = Field(description="The action to take")
    when: date = Field(description="Due date")
    criticality: Literal["high", "medium", "low"] = Field(description="Priority")

    @field_validator("who")
    @classmethod
    def who_not_empty(cls, v: str) -> str:
        assert v.strip(), "who must not be empty"
        return v.strip()

    @field_validator("when")
    @classmethod
    def when_not_too_old(cls, v: date) -> date:
        assert v >= date(2020, 1, 1), f"Date {v} is unreasonably old"
        return v


class MeetingTodos(BaseModel):
    todos: list[Todo]
    meeting_date: date
    attendees: list[str]

    @field_validator("meeting_date")
    @classmethod
    def meeting_date_not_too_old(cls, v: date) -> date:
        assert v >= date(2020, 1, 1), f"Meeting date {v} is unreasonably old"
        return v


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


@dataclass
class NoDuplicateTodos(Evaluator):
    @override
    async def evaluate(
        self, ctx: EvaluatorContext[str, MeetingTodos]
    ) -> EvaluationReason:
        seen: set[tuple[str, str]] = set()
        for todo in ctx.output.todos:
            key = (todo.who.lower(), todo.what.lower())
            if key in seen:
                return EvaluationReason(
                    value=0.0, reason=f"Duplicate: {todo.who} / {todo.what}"
                )
            seen.add(key)
        return EvaluationReason(
            value=1.0, reason=f"No dupes in {len(ctx.output.todos)} todos"
        )


rubric = "- TODOs should be clear, concise, and actionable.\n- No hallucinated goals."

dataset = Dataset(
    cases=[
        Case(
            name="Stand up",
            inputs=t1,
            expected_output=7,
            evaluators=(EqualsExpected(),),
        ),
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
    init_telemetry(project_name="edd-workshop")
    asyncio.run(evaluate())

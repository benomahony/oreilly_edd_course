import asyncio
from dataclasses import dataclass
from datetime import date
from typing import Literal
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import EqualsExpected, EvaluationReason, Evaluator, EvaluatorContext, LLMJudge
from typing_extensions import override

model = OpenAIChatModel("qwen/qwen3.6-35b-a3b@q4_k_m", provider=OpenAIProvider(base_url="http://localhost:1234/v1", api_key="lm-studio"))
Priority = Literal["high", "medium", "low"]


class Todo(BaseModel):
    who: str = Field(description="Who is responsible", min_length=1, max_length=100)
    what: str
    when: date
    priority: Priority


class MeetingTodos(BaseModel):
    todos: list[Todo]
    meeting_date: date
    attendees: list[str]


def load_transcript(transcript: str) -> str:
    with open(transcript) as f:
        return f.read()


transcript1 = load_transcript("src/oreilly_edd_course/transcript1.txt")
transcript2 = load_transcript("src/oreilly_edd_course/transcript2.txt")
transcript3 = load_transcript("src/oreilly_edd_course/transcript3.txt")


async def extract_todos(transcript: str) -> MeetingTodos:
    agent = Agent(model=model, output_type=MeetingTodos, retries=4, instructions="Extract ALL todos.")
    return (await agent.run(transcript)).output


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


rubric = "- TODOs should be clear, concise, and actionable.\n- No hallucinated goals."
pydantic_llmjudge = LLMJudge(model=model, rubric=rubric)

dataset = Dataset(
    cases=[
        Case(name="Stand up meeting", inputs=transcript1, expected_output=7, evaluators=(EqualsExpected(),)),
        Case(name="Product Planning Meeting", inputs=transcript2),
        Case(name="Client Onboarding Call", inputs=transcript3),
    ],
    evaluators=[pydantic_llmjudge, NoDuplicateTodos()],
)


async def evaluate():
    report = await dataset.evaluate(extract_todos)
    report.print(include_input=True, include_output=True, include_reasons=True)
    passed = sum(1 for c in report.cases if all(r.value for r in c.assertions.values()))
    failed = len(report.cases) - passed
    print(f"\nSUMMARY: {passed} passed, {failed} failed")
    assert failed == 0


if __name__ == "__main__":
    asyncio.run(evaluate())

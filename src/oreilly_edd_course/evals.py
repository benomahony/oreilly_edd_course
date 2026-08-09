"""
Step 1: Basic Evals — Exercise.

Fill in the TODOs to build a comprehensive eval suite.
"""

import asyncio
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import EqualsExpected, LLMJudge

model = OpenAIChatModel(
    "qwen/qwen3.6-35b-a3b@q4_k_m",
    provider=OpenAIProvider(base_url="http://localhost:1234/v1", api_key="lm-studio"),
)

Criticality = Literal["high", "medium", "low"]
TodoTheme = Literal["Coordination Task", "Code Review", "Other"]


class Todo(BaseModel):
    who: str = Field(description="Who is responsible", min_length=1, max_length=100)
    what: str
    when: date
    criticality: Criticality
    theme: TodoTheme


class MeetingTodos(BaseModel):
    todos: list[Todo]
    meeting_date: date
    attendees: list[str]


def load_transcript(path: str) -> str:
    with open(path) as f:
        return f.read()


transcript1 = load_transcript("src/oreilly_edd_course/transcript1.txt")
transcript2 = load_transcript("src/oreilly_edd_course/transcript2.txt")
transcript3 = load_transcript("src/oreilly_edd_course/transcript3.txt")


async def extract_todos(transcript: str) -> MeetingTodos:
    agent = Agent(
        model=model,
        output_type=MeetingTodos,
        retries=4,
        instructions="Extract ALL todos from the transcript as structured data.",
    )
    result = await agent.run(transcript)
    return result.output


# TODO 1: Add an EqualsExpected evaluator to transcript1 checking for 7 todos
# TODO 2: Add LLMJudge as a dataset-level evaluator
rubric = "- TODOs should be clear, concise, and actionable.\n- No hallucinated goals."
pydantic_llmjudge = LLMJudge(model=model, rubric=rubric)

dataset = Dataset(
    cases=[
        Case(name="Stand up meeting", inputs=transcript1),
        Case(name="Product Planning Meeting", inputs=transcript2),
        Case(name="Client Onboarding Call", inputs=transcript3),
    ],
    evaluators=[pydantic_llmjudge],
)


# TODO 3: Run, print results, and assert all cases pass

async def evaluate():
    report = await dataset.evaluate(extract_todos)
    report.print(include_input=True, include_output=True, include_reasons=True)


if __name__ == "__main__":
    asyncio.run(evaluate())
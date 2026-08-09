"""
Step 1: Structured Extraction & Evals — Exercise.

Build Pydantic models with validators, extract structured data with an agent,
then evaluate the quality with LLMJudge and custom evaluators.
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


# TODO 1: Add field_validator to ensure 'who' is not empty
# TODO 2: Add field_validator to ensure 'when' is not before 2020

class Todo(BaseModel):
    who: str = Field(description="Person responsible", min_length=1)
    what: str = Field(description="The action to take")
    when: date = Field(description="Due date")
    criticality: Literal["high", "medium", "low"] = Field(description="Priority")


# TODO 3: Add field_validator to ensure meeting_date is not before 2020

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


# TODO 4: Set output_type=MeetingTodos and retries=4 so the agent
# returns validated Pydantic models and retries on validation failure

async def extract_todos(transcript: str) -> MeetingTodos:
    agent = Agent(
        model=model,
        instructions="Extract ALL todos from the transcript as structured data.",
    )
    return (await agent.run(transcript)).output


# TODO 5: Add an EqualsExpected evaluator to the "Stand up" case
# Transcript 1 has exactly 7 action items.

# TODO 6: Create a custom evaluator that checks for duplicate todos
# (same who + what combination appearing more than once)

# TODO 7: Run the evals, print results, and assert all pass

rubric = "- TODOs should be clear, concise, and actionable.\n- No hallucinated goals."

dataset = Dataset(
    cases=[
        Case(name="Stand up", inputs=t1),
        Case(name="Product Planning", inputs=t2),
        Case(name="Client Onboarding", inputs=t3),
    ],
    evaluators=[LLMJudge(model=model, rubric=rubric)],
)


async def evaluate():
    report = await dataset.evaluate(extract_todos)
    report.print(include_input=True, include_output=True, include_reasons=True)


if __name__ == "__main__":
    asyncio.run(evaluate())
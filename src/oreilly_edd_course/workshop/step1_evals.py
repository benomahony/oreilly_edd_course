"""
Step 1: Evals for the Action Extractor — Exercise.

Fill in the TODOs to build a comprehensive eval suite using pydantic-evals.
"""

import asyncio
from datetime import date
from typing import Literal

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import EqualsExpected, LLMJudge

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


# ── TODO 1: Add an EqualsExpected evaluator to the "Stand up" case ──
# Transcript 1 has exactly 7 action items. Assert that the agent finds all 7.

# ── TODO 2: Add a dataset-level LLMJudge evaluator ──
# Use a rubric that checks for clear, concise, actionable TODOs
# with no hallucinated goals.

# ── TODO 3: Run the evals, print results, and assert all pass ──

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
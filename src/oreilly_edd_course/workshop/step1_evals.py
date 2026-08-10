"""
Step 1: Structured Extraction & Evals — Exercise.

Build a system that extracts structured action items from meeting transcripts,
then evaluate how well it works.
"""

import asyncio

from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

model = OpenAIChatModel(
    "qwen/qwen3.6-35b-a3b",
    provider=OpenAIProvider(base_url="http://localhost:1234/v1", api_key="lm-studio"),
)


# ── Your models here ──
# What fields does a todo need? What could go wrong?
# class Todo(BaseModel): ...
# class MeetingTodos(BaseModel): ...


def load_transcript(path: str) -> str:
    with open(path) as f:
        return f.read()


t1 = load_transcript("src/oreilly_edd_course/workshop/transcript1.txt")
t2 = load_transcript("src/oreilly_edd_course/workshop/transcript2.txt")
t3 = load_transcript("src/oreilly_edd_course/workshop/transcript3.txt")


# ── Your agent here ──
# async def extract_todos(transcript: str) -> MeetingTodos: ...


# ── Your evaluators here ──
# What does "good" look like? How do you measure it?
# dataset = Dataset(...)


async def evaluate():
    # Run your evals and check the results
    pass


if __name__ == "__main__":
    asyncio.run(evaluate())


"""
Step 1: Structured Extraction & Evals — Exercise.

Build a system that extracts structured action items from meeting transcripts,
then evaluate how well it works.
"""

import asyncio

from oreilly_edd_course.providers import get_model
from oreilly_edd_course.telemetry import init_telemetry

model = get_model()


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
    print("Step 1 is a stub. See step1_evals_solution.py for the reference.")


if __name__ == "__main__":
    init_telemetry(project_name="edd-workshop")
    asyncio.run(evaluate())


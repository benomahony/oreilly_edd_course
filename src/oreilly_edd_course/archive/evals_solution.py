import ast
import asyncio
from datetime import date
from typing import Literal
from pydantic import BaseModel, Field, field_validator
from pydantic_ai import Agent
from pydantic_evals import Dataset, Case
from pydantic_evals.evaluators import LLMJudge

Priority = Literal["high", "medium", "low"]


class Todo(BaseModel):
    who: str = Field(description="Who is responsible for this todo", min_length=1, max_length=100)
    what: str
    when: date
    priority: Priority


class MeetingTodos(BaseModel):
    todos: list[Todo]
    meeting_date: date
    attendees: list[str]
    code: str


    @field_validator("code")
    def is_valid_pthon(cls, v):
        if ast.parse(v):
            return v
        else:
            raise ValueError("Not valid python")


    @field_validator("meeting_date")
    def validate_meeting_date(cls, v):
        if v != date.today():
            raise ValueError("Meeting date must be today")
        return v


def load_transcript(transcript: str) -> str:
    with open(transcript, "r") as f:
        return f.read()


transcript1 = load_transcript("src/oreilly_edd_course/transcript1.txt")
transcript2 = load_transcript("src/oreilly_edd_course/transcript2.txt")
transcript3 = load_transcript("src/oreilly_edd_course/transcript3.txt")


async def extract_todos(transcript: str) -> MeetingTodos:
    todo_agent = Agent(
        model="anthropic:claude-3-7-sonnet-latest",
        instructions="""
    You are a task-oriented assistant that can extract todos from a transcript.
    """,
        output_type=MeetingTodos,
    )
    todos = await todo_agent.run(transcript)
    return todos.output


rubric = """
- TODOs should be clear and concise.
- TODOs should be actionable.
- TODOs should be assigned to a specific person.
"""
pydantic_llmjudge = LLMJudge(
    model="anthropic:claude-3-7-sonnet-latest",
    rubric=rubric,
)


dataset = Dataset(
    cases=[
        Case(name="Stand up meeting", inputs=transcript1),
        Case(
            name="Product Planning Meeting",
            inputs=transcript2,
        ),
        Case(
            name="Client Onboarding Call ",
            inputs=transcript3,
        ),
    ],
    evaluators=[pydantic_llmjudge],
)


async def evaluate():
    report = await dataset.evaluate(extract_todos)

    report.print(include_input=True, include_output=True, include_reasons=True)


if __name__ == "__main__":
    asyncio.run(evaluate())


for mode in ["claude-3-7-sonnet-latest

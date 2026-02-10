# TODO: Priortize
# TODO: sematic equivalence between them
# TODO: domain knowledge of how to extract todo from transcript
# TODO: Answer contains all todos
# TODO: task that can carry forward to the next day if not complete

from typing import Literal
from pydantic import BaseModel, field_validator
from pydantic_ai import Agent
from datetime import date
from difflib import unified_diff
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax


def load_transcript(transcript: str) -> str:
    with open(transcript, "r") as f:
        return f.read()


Priority = Literal["high", "medium", "low"]


class Todo(BaseModel):
    who: str
    what: str
    when: date
    priority: Priority


class MeetingTodos(BaseModel):
    todos: list[Todo]
    meeting_date: date
    attendees: list[str]

    @field_validator("meeting_date")
    def validate_meeting_date(cls, v):
        if v != date.today():
            raise ValueError("Meeting date must be today")
        return v


def main(transcript: str) -> MeetingTodos:
    transcript = load_transcript(transcript)
    agent = Agent(
        model="anthropic:claude-sonnet-4-5",
        instructions="""
    You are a task-oriented assistant that can extract todos from a transcript.
    """,
        output_type=MeetingTodos,
    )
    return agent.run_sync(transcript).output


result = main("src/oreilly_edd_course/transcript1.txt")

print(result)

assert result.todos[0].who == "Alex Kim", "The who is not an exact match"
assert result.todos[0].when == date(2026, 2, 9), (
    f"The when date is not an exact match got {result.when}"
)

expected_output = (
    "send Redis cluster details and connection pooling config to Marcus Rodriguez"
)
actual = result.todos[0].what

console = Console()

diff = "\n".join(
    unified_diff(
        expected_output.splitlines(),
        actual.splitlines(),
        lineterm="",
    )
)

console.print(Panel(Syntax(diff, "diff"), title="Diff"))


assert (
    result.todos[0].what.lower()
    == "send redis cluster details and connection pooling config to marcus rodriguez"
), f"The what is not an exact match got {result.what}"

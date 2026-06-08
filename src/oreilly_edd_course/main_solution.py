from typing import Literal
from pydantic import BaseModel, field_validator
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
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
        if v < date(2020, 1, 1):
            raise ValueError("Meeting date seems unreasonably old")
        return v


def main(transcript: str) -> MeetingTodos:
    transcript = load_transcript(transcript)
    model = OpenAIChatModel(
        "qwen/qwen3.6-35b-a3b@q4_k_m",
        provider=OpenAIProvider(
            base_url="http://localhost:1234/v1",
            api_key="lm-studio",
        ),
    )
    agent = Agent(
        model,
        instructions="""
    You are a task-oriented assistant that can extract todos from a transcript.
    Return your response as valid JSON matching the MeetingTodos schema.
    Include ALL todos from the transcript, even if some fields are unclear.
    """,
        output_type=MeetingTodos,
        retries=5,
    )
    return agent.run_sync(transcript).output


result = main("src/oreilly_edd_course/transcript1.txt")

print(result)

assert result.todos[0].who == "Alex Kim", "The who is not an exact match"
assert result.todos[0].when == date(2026, 1, 9), (
    f"The when date is not an exact match got {result.todos[0].when}"
)

expected_output = (
    "Send Redis cluster details and connection pooling config to Marcus Rodriguez"
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
), f"The what is not an exact match got {result.todos[0].what}"

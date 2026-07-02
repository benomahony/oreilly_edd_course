"""Code Along 1 solution: structured input/output + more assertions.

Picks up where exercise.py leaves off:
5. Add structured input & output (ActionItems instead of free text)
6. Add more assertions (specific fields, not just "contains")
"""

from datetime import date

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from rich.console import Console
from rich.panel import Panel

from oreilly_edd_course.core.diffing import diff_text
from oreilly_edd_course.core.transcripts import load_transcript
from oreilly_edd_course.models import ActionItems

model = OpenAIChatModel(
    "qwen/qwen3.6-35b-a3b@q4_k_m",
    provider=OpenAIProvider(
        base_url="http://localhost:1234/v1",
        api_key="lm-studio",
    ),
)

INSTRUCTIONS = """
You are an action item generator. You will be given a meeting transcript and you
will generate a structured list of action items. Capture each action item's
owner by name. Only fill in an owner's email if the transcript actually states
one - do not invent one. Use the meeting date as an action item's due date
unless a more specific date is mentioned.
"""


def generate_action_items(transcript: str) -> ActionItems:
    agent = Agent(model, instructions=INSTRUCTIONS, output_type=ActionItems, retries=3)
    return agent.run_sync(transcript).output


if __name__ == "__main__":
    transcript = load_transcript("transcript1")
    result = generate_action_items(transcript)
    print(result)

    assert result.action_items, "Expected at least one action item"
    assert result.action_items[0].owner.name == "Alex Kim", (
        f"Expected Alex Kim, got {result.action_items[0].owner.name}"
    )
    assert result.action_items[0].when == date(2026, 1, 9), (
        f"Expected the meeting date as the due date, got {result.action_items[0].when}"
    )

    expected_task = "Send Redis cluster details and connection pooling config to Marcus Rodriguez"
    actual_task = result.action_items[0].task

    console = Console()
    console.print(Panel(diff_text(expected_task, actual_task), title="Task diff"))

    # Equality evals only work when an exact match is required - the diff above
    # shows how they break on harmless rephrasing of free text:
    # assert actual_task.lower() == expected_task.lower()  # brittle!
    # Contains evals check for what actually matters and survive rewording:
    task = actual_task.lower()
    assert "redis" in task, f"Expected the Redis task first, got: {actual_task!r}"
    assert "marcus rodriguez" in task, f"Expected Marcus as the recipient, got: {actual_task!r}"

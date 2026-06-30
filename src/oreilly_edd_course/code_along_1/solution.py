"""Code Along 1 solution: structured input/output + more assertions.

Picks up where exercise.py leaves off:
5. Add structured input & output (ActionItems instead of free text)
6. Add more assertions (specific fields, not just "contains")
"""

from datetime import date

from pydantic_ai import Agent
from rich.console import Console
from rich.panel import Panel

from oreilly_edd_course.core.config import get_model
from oreilly_edd_course.core.diffing import diff_text
from oreilly_edd_course.core.transcripts import load_transcript
from oreilly_edd_course.models import ActionItems

INSTRUCTIONS = """
You are an action item generator. You will be given a meeting transcript and you
will generate a structured list of action items. For each action item, capture
the owner's name and infer a plausible corporate email (first.last@company.com)
since the transcript does not state emails explicitly. Use the meeting date as
an action item's due date unless a more specific date is mentioned.
"""


def generate_action_items(transcript: str) -> ActionItems:
    agent = Agent(get_model(), instructions=INSTRUCTIONS, output_type=ActionItems, retries=3)
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

    # This kind of exact-match assertion is brittle (see Code Along 2: it's
    # exactly the "Equality Evals" problem the course migrates away from).
    assert actual_task.lower() == expected_task.lower(), (
        f"Task is not an exact match, got: {actual_task!r}"
    )

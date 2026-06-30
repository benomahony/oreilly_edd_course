"""Code Along 2 solution.

Builds on exercise.py's Dataset (the fixed eval bar) and adds:
3. Validation moved into the agentic loop: a model_validator raises ValueError,
   which pydantic-ai treats as a failed structured-output attempt and retries
   the model with the validation error as feedback. The agent self-corrects
   *during* the run instead of being checked only afterwards with an assert.
"""

import asyncio

from pydantic import model_validator
from pydantic_ai import Agent

from oreilly_edd_course.code_along_2.exercise import dataset
from oreilly_edd_course.core.config import get_model
from oreilly_edd_course.models import ActionItems


class ValidatedActionItems(ActionItems):
    """ActionItems with a cross-field check enforced inside the agent's retry loop."""

    @model_validator(mode="after")
    def owners_must_be_attendees(self) -> "ValidatedActionItems":
        attendee_names = {person.name for person in self.attendees}
        for item in self.action_items:
            if item.owner.name not in attendee_names:
                raise ValueError(f"Action item owner {item.owner.name!r} is not a meeting attendee")
        return self


INSTRUCTIONS = """
You are an action item generator. You will be given a meeting transcript and you
will generate a structured list of action items. Every action item's owner must
also appear in the attendees list. Infer a plausible corporate email
(first.last@company.com) for each person, and use the meeting date as an action
item's due date unless a more specific date is mentioned.
"""


async def extract_action_items(transcript: str) -> ValidatedActionItems:
    agent = Agent(
        get_model(),
        instructions=INSTRUCTIONS,
        output_type=ValidatedActionItems,
        retries=4,
    )
    result = await agent.run(transcript)
    return result.output


async def evaluate() -> None:
    report = await dataset.evaluate(extract_action_items)
    report.print(include_input=True, include_output=True, include_reasons=True)


if __name__ == "__main__":
    asyncio.run(evaluate())

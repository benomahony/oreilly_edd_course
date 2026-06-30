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
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from oreilly_edd_course.code_along_2.exercise import dataset
from oreilly_edd_course.models import ActionItems

model = OpenAIChatModel(
    "qwen/qwen3.6-35b-a3b@q4_k_m",
    provider=OpenAIProvider(
        base_url="http://localhost:1234/v1",
        api_key="lm-studio",
    ),
)


class ValidatedActionItems(ActionItems):
    """ActionItems with a deterministic check enforced inside the agent's retry loop."""

    @model_validator(mode="after")
    def due_dates_not_before_meeting(self) -> "ValidatedActionItems":
        for item in self.action_items:
            if item.when < self.meeting_date:
                raise ValueError(
                    f"Action item {item.task!r} has a due date before the meeting date"
                )
        return self


INSTRUCTIONS = """
You are an action item generator. You will be given a meeting transcript and you
will generate a structured list of action items. Capture each action item's
owner by name. Only fill in an owner's email if the transcript actually states
one - do not invent one. An action item's due date must never be before the
meeting date; use the meeting date itself unless a later date is mentioned.
"""


async def extract_action_items(transcript: str) -> ValidatedActionItems:
    agent = Agent(
        model,
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

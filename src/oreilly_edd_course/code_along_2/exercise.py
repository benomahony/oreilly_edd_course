"""Code Along 2: migrate to pydantic_evals, async, and move validation into the
agentic loop.

Goals (see the course outline):
1. Migrate the Code Along 1 assertions into a pydantic_evals Dataset
2. Migrate the agent to async
3. (solution.py) Move validation into the agentic loop - Pydantic validators +
   retries instead of post-hoc asserts

Eval-driven: the Dataset below is the eval bar, written before the agent exists.
Your job is to implement extract_action_items() so it passes.
"""

import asyncio
import sys
from collections.abc import Awaitable, Callable

from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import LLMJudge

from oreilly_edd_course.core.transcripts import load_transcript
from oreilly_edd_course.models import ActionItems

model = OpenAIChatModel(
    "qwen/qwen3.6-35b-a3b@q4_k_m",
    provider=OpenAIProvider(
        base_url="http://localhost:1234/v1",
        api_key="lm-studio",
    ),
)

transcript1 = load_transcript("transcript1")
transcript2 = load_transcript("transcript2")
transcript3 = load_transcript("transcript3")

rubric = """
- Every action item should be a single atomic task, not multiple actions joined together.
- Every action item must be assigned to a specific, named person.
- No action item should reference a goal that was never discussed in the transcript.
"""

dataset = Dataset[str, ActionItems, None](
    name="code_along_2",
    cases=[
        Case(name="standup_meeting", inputs=transcript1),
        Case(name="product_planning_meeting", inputs=transcript2),
        Case(name="client_onboarding_call", inputs=transcript3),
    ],
    evaluators=[LLMJudge(model=model, rubric=rubric, include_input=True)],
)


async def extract_action_items(transcript: str) -> ActionItems:
    raise NotImplementedError(
        "Build an async agent with output_type=ActionItems and pass `dataset` above."
    )


async def evaluate(task: Callable[[str], Awaitable[ActionItems]]) -> None:
    """Run the eval bar and exit red or green - the EDD loop needs a visible signal."""
    report = await dataset.evaluate(task)
    report.print(include_output=True, include_reasons=True)

    crashed = [failure.name for failure in report.failures]
    failed = [
        case.name
        for case in report.cases
        if not all(result.value for result in case.assertions.values())
    ]
    if crashed or failed:
        print(f"\nFAILED - crashed: {crashed or 'none'}, failed evals: {failed or 'none'}")
        sys.exit(1)
    print("\nPASSED - all cases met the eval bar")


if __name__ == "__main__":
    asyncio.run(evaluate(extract_action_items))

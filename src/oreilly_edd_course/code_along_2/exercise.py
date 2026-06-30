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


async def evaluate() -> None:
    report = await dataset.evaluate(extract_action_items)
    report.print(include_input=True, include_output=True, include_reasons=True)


if __name__ == "__main__":
    asyncio.run(evaluate())

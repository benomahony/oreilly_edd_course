"""
Quick inference smoke test against the configured provider.

Verifies the model is loaded and reachable before running the workshop steps.
Switch providers with PROVIDER=lmstudio|google|openai (see providers.py).
"""

import asyncio

from pydantic import BaseModel
from pydantic_ai import Agent

from oreilly_edd_course.providers import get_model

model = get_model()


class Todo(BaseModel):
    who: str
    what: str


async def main() -> None:
    agent = Agent(
        model=model,
        output_type=list[Todo],
        instructions="Extract todos from the transcript as structured data.",
    )
    result = await agent.run(
        "Alice will finalise the budget by Friday. Bob owns the Q3 roadmap."
    )
    print(result.output)


if __name__ == "__main__":
    asyncio.run(main())

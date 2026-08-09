"""
Step 2: Self-Improving Agent — Exercise.

Build an agent that improves its own instructions based on eval failures.
The pattern: run evals → collect failures → improver rewrites instructions → repeat.
"""

import asyncio
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import EqualsExpected

model = OpenAIChatModel("qwen/qwen3.6-35b-a3b@q4_k_m", provider=OpenAIProvider(base_url="http://localhost:1234/v1", api_key="lm-studio"))

INSTRUCTIONS_PATH = Path(__file__).parent / "improver_instructions.md"


def get_instructions() -> str:
    if INSTRUCTIONS_PATH.exists():
        return INSTRUCTIONS_PATH.read_text().strip()
    INSTRUCTIONS_PATH.write_text("Extract todos from the transcript.")
    return "Extract todos from the transcript."


def save_instructions(instructions: str) -> None:
    INSTRUCTIONS_PATH.write_text(instructions)
    print(f"  Saved to {INSTRUCTIONS_PATH}")


async def extract_todos(text: str) -> str:
    agent = Agent(model=model, instructions=get_instructions())
    result = await agent.run(text)
    assert isinstance(result.output, str)
    return result.output


class Improvement(BaseModel):
    instructions: str
    reason: str


async def improve_instructions(prompt: str) -> Improvement:
    agent = Agent(
        model=model,
        output_type=Improvement,
        instructions="Improve the instructions to fix the failures. Make minimum necessary changes.",
    )
    result = await agent.run(prompt)
    return result.output


# Small dataset for the improver to learn from
test_cases = [
    ("simple_todo", "Alex needs to send the report by Friday.", "- Alex: Send the report by Friday."),
    ("multiple_todos", "Sarah will review the PR. Marcus will deploy to production.", "- Sarah: Review the PR.\n- Marcus: Deploy to production."),
    ("no_todos", "The team discussed Kafka. Everyone agreed.", "No action items identified."),
]

dataset = Dataset[str, str, Any](
    cases=[Case(name=n, inputs=i, expected_output=e, evaluators=(EqualsExpected(),)) for n, i, e in test_cases],
)


async def main():
    for iteration in range(1, 6):
        print(f"\n--- Iteration {iteration} ---")
        print(f"Instructions: {get_instructions()[:60]}...")

        report = await dataset.evaluate(extract_todos)
        report.print(include_output=True, include_input=True, include_expected_output=True)

        failures = [
            f"Input: '{c.inputs}' → Expected: '{c.expected_output}' → Got: '{c.output}'"
            for c in report.cases
            for r in c.assertions.values()
            if not r.value
        ]

        if not failures:
            print("\n  All cases passed!")
            break

        print(f"\n  {len(failures)} failure(s)")

        # TODO: Build improvement prompt and call improve_instructions()
        # improvement_prompt = f"Current: {get_instructions()}\n\nFailures: ..."
        # improved = await improve_instructions(improvement_prompt)
        # save_instructions(improved.instructions)
    else:
        print("\n  Max iterations reached.")


if __name__ == "__main__":
    asyncio.run(main())
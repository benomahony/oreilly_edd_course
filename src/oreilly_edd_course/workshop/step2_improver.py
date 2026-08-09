"""
Step 2: Self-Improving Agent — Exercise.

Build an agent that improves its own instructions based on eval failures.
"""

import asyncio
from pathlib import Path

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

model = OpenAIChatModel("qwen/qwen3.6-35b-a3b@q4_k_m", provider=OpenAIProvider(base_url="http://localhost:1234/v1", api_key="lm-studio"))

INSTRUCTIONS_PATH = Path(__file__).parent / "improver_instructions.md"


def get_instructions() -> str:
    if INSTRUCTIONS_PATH.exists():
        return INSTRUCTIONS_PATH.read_text().strip()
    INSTRUCTIONS_PATH.write_text("Extract todos from the transcript.")
    return "Extract todos from the transcript."


def save_instructions(instructions: str) -> None:
    INSTRUCTIONS_PATH.write_text(instructions)


# ── Your agent ──
# async def extract_todos(text: str) -> str: ...


# ── Your improver ──
# What should the improver return? How do you structure the prompt?
# async def improve_instructions(prompt: str) -> ...: ...


# ── Your eval loop ──
# 1. Run evals against a small dataset
# 2. Collect failures
# 3. Feed failures + current instructions to the improver
# 4. Save improved instructions
# 5. Repeat until all pass or max iterations reached


async def main():
    pass


if __name__ == "__main__":
    asyncio.run(main())
"""
Step 3: CI Pipeline Evals — Exercise.

Build an eval runner that can run in CI — threshold checks, regression detection, machine-readable output.
"""

import asyncio
from pathlib import Path

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

model = OpenAIChatModel("qwen/qwen3.6-35b-a3b@q4_k_m", provider=OpenAIProvider(base_url="http://localhost:1234/v1", api_key="lm-studio"))


# ── Your models and agent ──
# (Reuse what you built in Step 1)


# ── Your CI runner ──
# What makes an eval runner suitable for CI?
# - Threshold checks (fail if score drops below X)
# - Regression detection (compare against last run)
# - Machine-readable output (JSON for dashboards)
# async def evaluate(threshold=0.5, baseline_path=None): ...


async def main():
    pass


if __name__ == "__main__":
    asyncio.run(main())
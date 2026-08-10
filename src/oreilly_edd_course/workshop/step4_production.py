"""
Step 4: Production Evals — Exercise.

Monitor live agent outputs: sample production traffic, evaluate quality,
track scores over time, detect drift.
"""

import asyncio
from pathlib import Path

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

model = OpenAIChatModel("qwen/qwen3.6-35b-a3b", provider=OpenAIProvider(base_url="http://localhost:1234/v1", api_key="lm-studio"))


# ── Your models and agent ──
# (Reuse what you built in Step 1)


# ── Your production monitor ──
# How do you evaluate an agent in production vs in CI?
# - Sample a fraction of real requests
# - Run LLMJudge on the actual outputs
# - Log results for trend analysis
# - Detect when quality is degrading (drift)
# class ProductionMonitor: ...


# ── Your simulation ──
# Simulate production traffic and check for drift
# async def main(): ...


if __name__ == "__main__":
    asyncio.run(main())

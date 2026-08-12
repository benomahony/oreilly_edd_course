"""
Step 4: Production Evals — Exercise.

Monitor live agent outputs: sample production traffic, evaluate quality,
track scores over time, detect drift.
"""

import asyncio
from pathlib import Path

from pydantic_ai import Agent
from oreilly_edd_course.providers import get_model
from oreilly_edd_course.telemetry import init_telemetry

model = get_model()


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


async def main():
    print("Step 4 is a stub. See step4_production_solution.py for the reference.")


if __name__ == "__main__":
    init_telemetry(project_name="edd-workshop")
    asyncio.run(main())

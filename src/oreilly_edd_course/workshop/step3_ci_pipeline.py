"""
Step 3: CI Pipeline Evals — Exercise.

Build an eval runner that can run in CI — threshold checks, regression detection, machine-readable output.
"""

import asyncio
from pathlib import Path

from pydantic_ai import Agent
from oreilly_edd_course.providers import get_model
from oreilly_edd_course.telemetry import init_telemetry

model = get_model()


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
    init_telemetry(project_name="edd-workshop")
    asyncio.run(main())

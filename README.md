# O'REILLY EDD COURSE

Exercises from the O'Reilly Eval-Driven Development course.

## Setup

```bash
uv sync
```

Install [LM Studio](https://lmstudio.ai/), download a model (e.g., `qwen/qwen3.6-35b-a3b `), start the local server at `http://localhost:1234`.

## Workshop

Four progressive steps in `src/oreilly_edd_course/workshop/`. Each has an exercise file (with `TODO` markers) and a solution.

### Step 1: Evals for the Action Extractor

Walk through all eval types using `pydantic-evals`: LLMJudge, EqualsExpected, custom evaluators.

```bash
uv run src/oreilly_edd_course/workshop/step1_evals.py
uv run src/oreilly_edd_course/workshop/step1_evals_solution.py
```

### Step 2: Self-Improving Agent

The eval-feedback-improve loop: run evals → collect failures → improver rewrites instructions → repeat.

```bash
uv run src/oreilly_edd_course/workshop/step2_improver.py
uv run src/oreilly_edd_course/workshop/step2_improver_solution.py
```

### Step 3: CI Pipeline Evals

Run evals as a CI gate before deploying: threshold-based pass/fail, regression detection, JSON export.

```bash
uv run src/oreilly_edd_course/workshop/step3_ci_pipeline.py
uv run src/oreilly_edd_course/workshop/step3_ci_pipeline_solution.py
```

### Step 4: Production Evals (Monitoring)

Monitor live agent outputs after deploy: sample traffic, LLMJudge on real outputs, track scores over time, detect drift.

```bash
uv run src/oreilly_edd_course/workshop/step4_production.py
uv run src/oreilly_edd_course/workshop/step4_production_solution.py
```

## Archive

Original exercise files from the first course are in `src/oreilly_edd_course/archive/` for reference.

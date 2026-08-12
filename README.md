# O'REILLY EDD COURSE

Exercises from the O'Reilly Eval-Driven Development course.

## Setup

```bash
uv sync
```

Install [LM Studio](https://lmstudio.ai/), download a model (e.g., `meta/muse-glimmer`), start the local server at `http://localhost:1234`.

## Workshop

Four progressive steps in `src/oreilly_edd_course/workshop/`. Each has an exercise file (with `TODO` markers) and a solution.

### Step 1: Structured Extraction & Evals

Define `Todo` and `MeetingTodos` Pydantic models, then evaluate extraction accuracy using `pydantic-evals`: `EqualsExpected`, `LLMJudge`, and custom evaluators.

```bash
uv run src/oreilly_edd_course/workshop/step1_evals.py
uv run src/oreilly_edd_course/workshop/step1_evals_solution.py
```

### Step 2: Self-Improving Agent

The eval-feedback-improve loop: run evals on structured extraction → collect failures → improver rewrites instructions → repeat.
Imports `extract_todos`, `Todo`, `MeetingTodos`, and transcripts from Step 1, then re-runs the extraction agent with improved instructions.

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

Original exercise files from the first course are in `src/oreilly_edd_course/archive/` for reference. These use `main_solution.py` and `evals_solution.py` with the first iteration of the structured extraction approach.

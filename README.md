# O'REILLY EDD COURSE

Exercises from the O'Reilly Eval-Driven Development course.

A progressive walkthrough of Eval-Driven Development: from basic agent extraction, through comprehensive evals, self-improving agents, CI pipelines, and production monitoring.

## Setup

```bash
uv sync
```

Install [LM Studio](https://lmstudio.ai/), download a model (e.g., `qwen/qwen3.6-35b-a3b@q4_k_m`), start the local server at `http://localhost:1234`.

## Course Structure

Each step has an exercise file (with `TODO` markers) and a solution.

### Step 0: Warm-up — Basic Agent

Extract structured todos from a meeting transcript.

```bash
uv run src/oreilly_edd_course/main.py
```

### Step 1: Evals for the Action Extractor

Walk through all eval types using `pydantic-evals`: LLMJudge, EqualsExpected, custom evaluators, and dataset-level aggregation.

```bash
uv run src/oreilly_edd_course/evals.py          # exercise
uv run src/oreilly_edd_course/evals_solution.py  # solution
```

**Key concepts:** `Evaluator` protocol, `EvaluationReason`, combining evaluator types, pass/fail aggregation.

### Step 2: Self-Improving Agent

An agent that improves its own instructions based on eval failures — inspired by the [ai-agent-katas](https://github.com/benomahony/ai-agent-katas) `self_improving_agent`. The loop: run evals → collect failures → feed to improver agent → save improved instructions → repeat.

```bash
uv run src/oreilly_edd_course/improver_agent.py          # exercise
uv run src/oreilly_edd_course/improver_agent_solution.py  # solution
```

**Key concepts:** eval-feedback-improve loop, LLM debugging LLM, minimum-necessary-change principle.

### Step 3a: CI Pipeline Evals

Run evals as a CI gate: threshold-based pass/fail, regression detection against baselines, JSON export for dashboards. This is what you run before deploying — it tells you whether to ship.

```bash
uv run src/oreilly_edd_course/ci_pipeline_evals.py          # exercise
uv run src/oreilly_edd_course/ci_pipeline_evals_solution.py  # solution
```

**Key concepts:** evals as a CI gate, regression detection, machine-readable output, configurable thresholds.

### Step 3b: Production Evals (Monitoring)

Monitor live agent outputs in production: evaluate every N-th request using LLMJudge, track scores over time, detect drift, and alert on degradation. This is what runs after deploy — it tells you whether things are getting worse.

```bash
uv run src/oreilly_edd_course/production_evals.py          # exercise
uv run src/oreilly_edd_course/production_evals_solution.py  # solution
```

**Key concepts:** sampling production traffic, LLMJudge on real outputs, drift detection, JSONL logging for observability.

## File Reference

| File | Purpose |
|---|---|
| `main.py` / `main_solution.py` | Step 0: Basic agent |
| `evals.py` / `evals_solution.py` | Step 1: Comprehensive evals |
| `improver_agent.py` / `improver_agent_solution.py` | Step 2: Self-improving agent |
| `improver_instructions.md` | Instructions file improved iteratively |
| `ci_pipeline_evals.py` / `ci_pipeline_evals_solution.py` | Step 3a: CI gate evals |
| `production_evals.py` / `production_evals_solution.py` | Step 3b: Production monitoring |
| `transcript1.txt` | Engineering standup (7 action items) |
| `transcript2.txt` | Product planning meeting |
| `transcript3.txt` | Client onboarding call |
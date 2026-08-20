# O'REILLY EDD COURSE

Exercises from the O'Reilly Eval-Driven Development course.

## Setup

```bash
uv sync
```

Install [LM Studio](https://lmstudio.ai/), download a model (e.g., `meta/muse-glimmer`), start the local server at `http://localhost:1234`.

## Workshop

Two parts in `src/oreilly_edd_course/workshop/`: a hands-on exercise to learn on, and a demo that ties the whole eval-driven-development loop together.

### Step 1: Structured Extraction & Evals (exercise)

Define `Todo` and `MeetingTodos` Pydantic models, then evaluate extraction accuracy using `pydantic-evals`: `LLMJudge` and custom evaluators (`TodoCount`, `NoDuplicateTodos`). The exercise file has `TODO` markers; a reference solution sits alongside it.

```bash
uv run src/oreilly_edd_course/workshop/step1_evals.py
uv run src/oreilly_edd_course/workshop/step1_evals_solution.py
```

### Step 2: The Full EDD Loop (demo)

A single run-it-and-watch showcase built on the Step 1 extractor:

- **Comprehensive evaluation** — structural (`TodoCount`, `NoDuplicateTodos`) + semantic (`LLMJudge`) + **lexical**: a [`lexguard`](https://pypi.org/project/lexguard/) lexicon that deterministically scores each todo for vague/weak phrasing.
- **Self-improvement** — run evals, collect failures, and let an improver agent rewrite the extraction instructions **and grow a custom `lexguard` lexicon** of vague phrasings it spots. The guardrail co-evolves with the agent.
- **Production monitoring** — simulate live traffic, run the cheap deterministic lexicon guard on 100% of it and a sampled `LLMJudge`, log to JSONL, and check for drift.

```bash
uv run src/oreilly_edd_course/workshop/step2_demo.py
```

## Archive

Original exercise files from the first course are in `src/oreilly_edd_course/archive/` for reference. These use `main_solution.py` and `evals_solution.py` with the first iteration of the structured extraction approach.

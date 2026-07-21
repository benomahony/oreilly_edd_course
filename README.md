# OREILLY EDD COURSE

Exercises from the O'Reilly *Eval Driven Development for Reliable Agents* course.

Running example throughout: turning a meeting transcript into structured action items.

## Setup

### Dependencies

```bash
uv sync
```

### Local Model (LM Studio)

1. Install [LM Studio](https://lmstudio.ai/) and launch it
2. Download a model (e.g., `llama-3.1-8b-instruct`)
3. Start the local server (the "Localhost Server" tab)
4. Verify the server is running at `http://localhost:1234`

The Agent connects to LM Studio's default OpenAI-compatible API endpoint at `http://localhost:1234/v1`.
Each `exercise.py`/`solution.py` builds its `OpenAIChatModel`/`OpenAIProvider` inline - if you're
on a different model or port, edit that one line directly in the file you're running.

## How this course works

Each code-along is a pair of files: `exercise.py` is the stub you implement against, and
`solution.py` is the reference answer. The evals (assertions, judges, datasets) are defined
*before* the agent code - that's the "eval driven" part. Your job is to make `exercise.py` pass
the evals already written into it.

## Exercises

| Code-along | What's new | Run the stub | Run the solution |
|---|---|---|---|
| 1: simple assertions + LLM-as-judge | plain-text agent, `assert`/`contains` checks, agent-as-judge, then structured `ActionItems` output | `uv run -m oreilly_edd_course.code_along_1.exercise` | `uv run -m oreilly_edd_course.code_along_1.solution` |
| 2: pydantic_evals + async + agentic validation | `Dataset`/`Case`/`LLMJudge`, async agent, validators that trigger retries inside the agent run | `uv run -m oreilly_edd_course.code_along_2.exercise` | `uv run -m oreilly_edd_course.code_along_2.solution` |

## Dev tooling

```bash
uv sync --group dev
uv run ruff check .
uv run ruff format .
```

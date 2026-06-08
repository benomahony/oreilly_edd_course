# OREILLY EDD COURSE

Exercises from the O'Reilly Event-Driven Data course.

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

## Exercise

Implement `main()` in `src/oreilly_edd_course/main.py` to extract structured todos from a meeting transcript.

See `main_solution.py` for the rough solution (from the first course).

## Running

Run the exercise stub:

```bash
uv run src/oreilly_edd_course/main.py
```

Run the solution:

```bash
uv run src/oreilly_edd_course/main_solution.py
```


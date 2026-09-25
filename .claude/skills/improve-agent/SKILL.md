---
name: improve-agent
description: Run the meeting-todos evals and iteratively improve the agent (prompt, tools, guardrails) until they pass. Use when asked to improve the agent, fix failing evals, or run improvement iterations. Optional argument is the max number of iterations (default 3).
---

# Improve the agent

Iterate: evaluate → change the agent → re-evaluate. Max iterations: the argument if given, else 3.

## What you may change

- `src/oreilly_edd_course/instructions.md` — the extractor's prompt
- `src/oreilly_edd_course/capabilities/` — capabilities (see below)

**Never edit** `src/oreilly_edd_course/example.py` (evals, golden dataset, thresholds) or
`src/oreilly_edd_course/transcripts/`. Passing by weakening the evals is not an improvement.
If an eval or golden answer looks wrong, stop and say so instead.

## Each iteration

1. Run `uv run edd run` and read the failure list at the end.
2. Pick the lever per failure:
   - **Prompt** (`instructions.md`) — judgement: what counts as a todo, owners, phrasing,
     priorities. Minimum change; keep what already works.
   - **Tool** (capability overriding `get_toolset`) — things code gets right and the model
     doesn't: date arithmetic, parsing speakers out of the transcript. Tools cost model
     requests; watch `MaxModelRequests`.
   - **Guardrail** (capability overriding `after_output_validate`, raising `ModelRetry`) —
     a failing reference-free check (`NoDuplicateTodos`, `ConciseTodos`, a lexguard lexicon…).
     Promote a lexguard eval using the same lexicon: shipped ones from `lexguard`, custom ones
     from `oreilly_edd_course.lexicons`.
3. Review capabilities the agent authored for itself (`capabilities/manifest.json`); set
   `"status": "disabled"` on any that aren't helping.
4. Re-run. Stop when everything passes, at max iterations, or when an iteration doesn't
   reduce the failure count (revert that iteration's changes first).

## Writing a capability

Write it to `capabilities/<name>.py` and add an entry to `capabilities/manifest.json`
(`name`, `module_file`, `class_name`, `"status": "active"`, `"last_error": null`) — or
use `CapabilityStore(Path("src/oreilly_edd_course/capabilities")).write(name, code)` from
`pydantic_ai_harness.capability_creation`, which validates and records it for you.
Exactly one `AbstractCapability` subclass with a no-argument constructor; the output is a
`MeetingTodos` (use attribute access, don't import it).

## Finish

Report the failure count per iteration, then show `git diff --stat src/oreilly_edd_course/`
and a one-line summary of each change. Don't commit — the user reviews and commits.

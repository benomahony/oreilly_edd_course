# Eval-Driven Development for Reliable Agents (O'Reilly)

One fully worked example of Eval-Driven Development: extract action items from
meeting transcripts, measure it with a layered eval suite, then let an improver
agent fix the failures — by rewriting the prompt **and** by authoring runtime
capabilities with [`CapabilityCreation`](https://pydantic.dev/docs/ai/harness/capability-creation/).
[Lexguard](https://github.com/benomahony/lexguard) lexicons do double duty as offline
evals and runtime guardrails.

## Setup

```bash
uv run edd setup   # installs deps, picks a provider (google / lmstudio), starts Phoenix
```

## Run

```bash
uv run edd run          # improve the committed agent
uv run edd run --fresh  # start over from the naive prompt
uv run edd obs     # open Phoenix to inspect the traces
```

Everything lives in [`src/oreilly_edd_course/example.py`](src/oreilly_edd_course/example.py),
in five sections:

1. **System under test** — `Todo` / `MeetingTodos` Pydantic models and the extraction agent,
   with always-on lexguard guardrails:
   - `InputGuardrail` — hard-fails on prompt `Injection` in the transcript.
   - `OutputGuardrail(lexguard_guard(Leakage))` — self-reference, system-prompt leaks,
     injection echoes, placeholders → retry with lexguard's fix.
   - `ENFORCE_TODO_WORDING = True` also enforces the per-todo lexicons at runtime.
2. **Golden dataset** — three transcripts with expected outputs.
3. **Evals**, cheapest first:
   | Layer | Evaluators |
   | --- | --- |
   | Schema | Pydantic validation (agent retries), `IsInstance` |
   | Deterministic, reference-free | `NoDuplicateTodos`, `AssigneesAreAttendees`, `DueDatesNotBeforeMeeting`, `ConciseTodos` |
   | Lexguard | per-todo `Vague`, `Hypothetical`, `Completion`, `ConditionalTrigger`, `Past`, `Hedging`; whole-output `Bloat`, `Servility`, `Overreach`, `Leakage`, `Confidential` |
   | Custom lexguard ([`lexicons.py`](src/oreilly_edd_course/lexicons.py)) | `TodoVerb` (extends `Actionable`, must be present), `StatusUpdate` (with `rules_out`), `VagueOwner` (on `who`) |
   | Deterministic, reference-based | `MeetingDateCorrect`, `AttendeesMatch`, `TodoCount`, `OwnerRecall` (score) |
   | LLM-as-judge | coverage vs. expected output, todo quality |
   | Typed judge | `JevJudge` on TypeSafe's [Jev](https://pydantic.dev/docs/ai/models/typesafe/): yes/no questions with a confidence each (set `TYPESAFE_API_KEY`) |
   | Operational | `MaxDuration`, `MaxModelRequests` |
4. **Improver** — an agent with two levers:
   - *Prompt*: returns new instructions, written to `agent/instructions.md`.
   - *Capability*: calls `author_capability(name, code)` to write a guardrail
     (an `AbstractCapability` with an `after_output_validate` hook that raises
     `ModelRetry`) to `agent/capabilities/`. It's validated immediately and
     injected into the extractor on the next run via `creation.store.load_active()`.
     A failing lexguard eval promotes straight to a guardrail using the same lexicon.
5. **Loop** — baseline eval → improve → re-eval (up to 3 times), then a diff of
   the final report against the baseline.

`agent/` is committed: each run builds on it, `git diff src/oreilly_edd_course/agent/`
shows what the improver changed, and committing keeps it. `--fresh` resets to the naive
prompt with no capabilities.

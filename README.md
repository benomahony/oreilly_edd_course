# Eval-Driven Development for Reliable Agents (O'Reilly)

One fully worked example of Eval-Driven Development: extract action items from
meeting transcripts, measure it with a layered eval suite, then let an improver agent
fix the failures by rewriting the prompt **and** by authoring runtime capabilities with
[`CapabilityCreation`](https://pydantic.dev/docs/ai/harness/capability-creation/).
[Lexguard](https://github.com/benomahony/lexguard) lexicons do double duty as offline
evals and runtime guardrails.

## Setup

```bash
export GOOGLE_API_KEY=...
uv run logfire auth && uv run logfire projects new   # optional: traces + online evals in your own Logfire
```

## Run

```bash
uv run edd run          # evaluate and improve the committed agent
uv run edd run --fresh  # start over from the naive prompt
uv run edd obs          # open Logfire: traces + online eval results
```

The example is split across three files in [`src/oreilly_edd_course/`](src/oreilly_edd_course/):
[`example.py`](src/oreilly_edd_course/example.py) (system under test, improver, loop),
[`evals.py`](src/oreilly_edd_course/evals.py) (golden dataset and evals) and
[`models.py`](src/oreilly_edd_course/models.py) (the output models).

1. **System under test** — the extraction agent (output: `Todo` / `MeetingTodos` in `models.py`),
   with always-on lexguard guardrails:
   - `InputGuardrail` — hard-fails on prompt `Injection` in the transcript.
   - `OutputGuardrail(lexguard_guard(Leakage))` — self-reference, system-prompt leaks,
     injection echoes, placeholders → retry with lexguard's fix.
2. **Golden dataset** (`evals.py`) — three transcripts with expected outputs.
3. **Evals** (`evals.py`), cheapest first:
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
4. **Improver** — an agent that reads the failures and pulls two levers:
   - *Prompt*: rewrites `instructions.md`.
   - *Capability*: calls `author_capability(name, code)` to write a tool, guardrail or other
     hook to `capabilities/`, validated immediately and live on the extractor's next run.
     A failing lexguard eval promotes straight to a guardrail using the same lexicon. It also
     reviews (and can disable) capabilities the extractor authored for itself — the extractor
     carries `CapabilityCreation` too.
5. **Loop** — baseline eval → improve → re-eval (up to 3 times), then a diff of the final
   report against the baseline.

`instructions.md` and `capabilities/` are committed: `git diff src/oreilly_edd_course/`
shows what changed, committing keeps it. `--fresh` resets to the naive prompt with no
capabilities.

# Eval-Driven Development for Reliable Agents (O'Reilly)

One fully worked example of Eval-Driven Development: extract action items from
meeting transcripts, measure it with a layered eval suite, then improve it by
rewriting the prompt **and** by authoring runtime capabilities with
[`CapabilityCreation`](https://pydantic.dev/docs/ai/harness/capability-creation/).
[Lexguard](https://github.com/benomahony/lexguard) lexicons do double duty as offline
evals and runtime guardrails.

## Setup

```bash
uv run edd setup   # installs deps, picks a provider (google / lmstudio)
```

## Run

```bash
uv run edd run          # evaluate the committed agent
uv run edd run --fresh  # start over from the naive prompt
uv run edd obs          # open Logfire: traces + online eval results
```

Everything lives in [`src/oreilly_edd_course/example.py`](src/oreilly_edd_course/example.py),
in four sections:

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
4. **Run** — evaluate, then list what's failing.

## Improving the agent

`example.py` is the fixed harness. The agent is improved around it:

- **Claude Code is the outer loop.** Run `/improve-agent [iterations]` (the project skill in
  `.claude/skills/`), or just ask it to run `edd run` and fix what's failing:
  it edits `instructions.md` or writes capabilities to `capabilities/` — tools,
  guardrails (a failing lexguard eval promotes straight to one using the same
  lexicon), or other hooks.
- **The agent improves itself.** The extractor carries `CapabilityCreation`, so it can
  author capabilities during its own runs; `creation.store.load_active()` injects
  them on the next one.

`instructions.md` and `capabilities/` are committed: `git diff src/oreilly_edd_course/`
shows what changed, committing keeps it. `--fresh` resets to the naive prompt with no
capabilities.

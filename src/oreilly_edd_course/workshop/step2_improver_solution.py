"""
Step 2: Self-Improving Agent — SOLUTION.

Completes the improvement loop: run evals → collect failures → improver rewrites instructions → repeat.
Imports the extraction agent from step 1 and feeds it improved instructions.
"""

import asyncio
from datetime import date
from pathlib import Path

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_evals import Case, Dataset

from oreilly_edd_course.providers import get_model
from oreilly_edd_course.telemetry import init_telemetry
from oreilly_edd_course.workshop.step1_evals_solution import (
    MeetingTodos,
    Todo,
    load_transcript,
    t1, t2, t3,
)

model = get_model()

INSTRUCTIONS_PATH = Path(__file__).parent / "improver_instructions.md"


def get_instructions() -> str:
    if INSTRUCTIONS_PATH.exists():
        return INSTRUCTIONS_PATH.read_text().strip()
    INSTRUCTIONS_PATH.write_text(
        "Extract todos from the transcript as a MeetingTodos object."
    )
    return "Extract todos from the transcript as a MeetingTodos object."


def save_instructions(instructions: str) -> None:
    INSTRUCTIONS_PATH.write_text(instructions)
    print(f"  Saved to {INSTRUCTIONS_PATH}")


# ── Re-wrap extract_todos with dynamic instructions ──
# The improver changes instructions; the same extraction agent runs with new ones.

async def extract_todos(text: str) -> MeetingTodos:
    agent = Agent(
        model=model,
        output_type=MeetingTodos,
        retries=4,
        instructions=get_instructions(),
    )
    return (await agent.run(text)).output


# ── Your improver ──

class Improvement(BaseModel):
    instructions: str
    reason: str


async def improve_instructions(prompt: str) -> Improvement:
    agent = Agent(
        model=model,
        output_type=Improvement,
        instructions="Improve the instructions to fix the failures. Make minimum necessary changes.",
    )
    result = await agent.run(prompt)
    return result.output


# ── Transcripts (from step 1) ──

transcript1 = t1
transcript2 = t2
transcript3 = t3


# ── Eval Cases ──

test_cases = [
    Case(
        name="standup_meeting",
        inputs=transcript1,
        expected_output=MeetingTodos(
            todos=[
                Todo(who="Alex Kim", what="Send Redis cluster details to Marcus Rodriguez", when=date(2026, 1, 9), criticality="high"),
                Todo(who="Alex Kim", what="Send connection pooling config to Marcus Rodriguez", when=date(2026, 1, 9), criticality="high"),
                Todo(who="Sarah Chen", what="Ping design team about mockups", when=date(2026, 1, 9), criticality="medium"),
                Todo(who="Marcus Rodriguez", what="Review Priya's PR #847 by end of day", when=date(2026, 1, 9), criticality="high"),
                Todo(who="Sarah Chen", what="Confirm Wednesday afternoon works for DB migration with Product", when=date(2026, 1, 10), criticality="medium"),
                Todo(who="Alex Kim", what="Schedule maintenance window for database migration", when=date(2026, 1, 9), criticality="medium"),
                Todo(who="Priya Patel", what="Create ticket for updating testing documentation", when=date(2026, 1, 9), criticality="low"),
            ],
            meeting_date=date(2026, 1, 9),
            attendees=["Sarah Chen", "Marcus Rodriguez", "Alex Kim", "Priya Patel"],
        ),
    ),
    Case(
        name="product_planning",
        inputs=transcript2,
        expected_output=MeetingTodos(
            todos=[
                Todo(who="Kevin Martinez", what="Research data warehouse options with cost estimates and migration timeline", when=date(2026, 1, 16), criticality="high"),
                Todo(who="Tom Richardson", what="Sync with Kevin mid-week on technical integration points", when=date(2026, 1, 14), criticality="medium"),
                Todo(who="Maya Johnson", what="Set up requirements calls with 3 enterprise customers", when=date(2026, 1, 14), criticality="high"),
                Todo(who="Maya Johnson", what="Line up 2-3 customers for user testing session", when=date(2026, 1, 14), criticality="medium"),
            ],
            meeting_date=date(2026, 1, 9),
            attendees=[
                "Jennifer Walsh",
                "Maya Johnson",
                "Tom Richardson",
                "Kevin Martinez",
                "Lisa Anderson",
            ],
        ),
    ),
    Case(
        name="client_onboarding",
        inputs=transcript3,
        expected_output=MeetingTodos(
            todos=[
                Todo(who="Robert Park", what="Get Okta attribute schema from security team", when=date(2026, 1, 10), criticality="high"),
                Todo(who="Amanda Chen", what="Talk to marketing team about using their project as test case", when=date(2026, 1, 10), criticality="medium"),
                Todo(who="Amanda Chen", what="Request Jira admin access for Robert Park", when=date(2026, 1, 10), criticality="high"),
                Todo(who="Amanda Chen", what="Audit custom Jira fields and document what they're used for", when=date(2026, 1, 17), criticality="high"),
            ],
            meeting_date=date(2026, 1, 9),
            attendees=["Rachel Foster", "Amanda Chen", "Robert Park", "David Park"],
        ),
    ),
]

dataset = Dataset[str, MeetingTodos, MeetingTodos](
    cases=test_cases,
)


async def main():
    for iteration in range(1, 6):
        print(f"\n--- Iteration {iteration} ---")
        print(f"Instructions: {get_instructions()[:60]}...")

        report = await dataset.evaluate(extract_todos)
        report.print(
            include_output=True, include_input=True, include_expected_output=True
        )

        failures = [
            f"Case '{c.name}': {r.reason or 'Assertion failed'}"
            for c in report.cases
            for r in c.assertions.values()
            if not r.value
        ]

        if not failures:
            print("\n  All cases passed!")
            break

        print(f"\n  {len(failures)} failure(s)")

        current = get_instructions()
        feedback = "Failures:\n" + "\n".join(failures)
        improvement_prompt = (
            f"Current instructions:\n{current}\n\n{feedback}\n\n"
            "Fix these failures with minimum changes to the instructions. "
            "The output must be valid MeetingTodos JSON with who/what/when/priority for each todo."
        )
        improved = await improve_instructions(improvement_prompt)
        save_instructions(improved.instructions)
        print(f"  Reason: {improved.reason}")
    else:
        print("\n  Max iterations reached.")


if __name__ == "__main__":
    init_telemetry(project_name="edd-workshop")
    asyncio.run(main())

"""Code Along 1: simple assertion-based evals + LLM-as-judge.

Goals (see the course outline):
1. Walk through the inputs - the meeting transcripts in data/
2. Define the list of evals we want to implement (below, BEFORE the agent exists)
3. Write the first simple assertions
4. Build the agent scaffold

Structured input/output and richer assertions are added in solution.py - that's
the natural next step once these simple evals pass.
"""

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from oreilly_edd_course.core.transcripts import load_transcript

model = OpenAIChatModel(
    "qwen/qwen3.6-35b-a3b@q4_k_m",
    provider=OpenAIProvider(
        base_url="http://localhost:1234/v1",
        api_key="lm-studio",
    ),
)

# Our list of evals to implement, written before any agent code exists:
# - The output should mention at least one real attendee from the transcript.
# - An LLM judge should agree every action item is a single, atomic, actionable task.

INSTRUCTIONS = """
You are an action item generator. You will be given a meeting transcript and you
will generate a list of action items. Return only the action items, one per line,
each stated as a single actionable task.
"""


def generate_action_items(transcript: str) -> str:
    agent = Agent(model, instructions=INSTRUCTIONS)
    return agent.run_sync(transcript).output


def llm_judge(action_items: str) -> bool:
    judge = Agent(
        model,
        retries=3,
        instructions="""
        You are a judge. Decide whether every action item below is a single,
        atomic, actionable task assigned to a specific person. Respond with
        only True or False.
        """,
        output_type=bool,
    )
    return judge.run_sync(f"Action items:\n{action_items}").output


if __name__ == "__main__":
    transcript = load_transcript("transcript1")
    result = generate_action_items(transcript)
    print(result)

    assert "Alex" in result, "Expected Alex Kim's action item to be present"
    assert llm_judge(result), "Judge rejected the action items as not atomic/actionable"

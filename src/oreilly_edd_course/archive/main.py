# Atomic single task per todo
# order is not important
# no hallucination of goals
# have a time/date for when to do the item by
# Todo has an assigned owner.
# avoid duplicating previously scheduled todos? like if these are stand-up notes, often have the same todo in multiple standups
# a good one would be easy or possible for llm to self verify
# Merge repeated or rephrased actions into one
# Tag criticality, dependencies, or themes ?
# bring all TODO o the same structure: Who/What/when


from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider


def load_transcript(transcript: str) -> str:
    with open(transcript, "r") as f:
        return f.read()


class JudgeOpinion(BaseModel):
    opinion: bool


def llm_judge(output: str) -> bool:
    model = OpenAIChatModel(
        "qwen/qwen3.6-35b-a3b@q4_k_m",
        provider=OpenAIProvider(
            base_url="http://localhost:1234/v1",
            api_key="lm-studio",
        ),
    )
    agent = Agent(
        model,
        retries=3,
        instructions="""
        The output should be an atomic single task per todo
        """,
        output_type=bool,
    )

    judge_input = f"Agent Output: {output}"

    result = agent.run_sync(judge_input)

    return result.output


def main(transcript: str) -> str:
    model = OpenAIChatModel(
        "qwen/qwen3.6-35b-a3b@q4_k_m",
        provider=OpenAIProvider(
            base_url="http://localhost:1234/v1",
            api_key="lm-studio",
        ),
    )
    agent = Agent(
        model,
        instructions="""
       return only action items 1 & 2 and always state action items in the singular.
        """,
    )

    loaded_transcript = load_transcript(transcript)
    return agent.run_sync(loaded_transcript).output


result = main("src/oreilly_edd_course/transcript1.txt")

print(result)

llm_judgement = llm_judge(result)

print(llm_judgement)

assert llm_judgement

# Atomic single task per todo
# order is not important
# no hallucination of goals
# avoid duplicating previously scheduled todos? like if these are stand-up notes, often have the same todo in multiple standups
# a good one would be easy or possible for llm to self verify
# Merge repeated or rephrased actions into one
# bring all TODO o the same structure: Who/What/when


import asyncio
from datetime import date
from typing import Literal
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import LLMJudge

# have a time/date for when to do the item by
# Todo has an assigned owner.
# Tag criticality, dependencies, or themes ?

model = OpenAIChatModel(
    "qwen/qwen3.6-35b-a3b@q4_k_m",
    provider=OpenAIProvider(
        base_url="http://localhost:1234/v1",
        api_key="lm-studio",
    ),
)

Criticality = Literal["high", "medium", "low"]
TodoTheme = Literal["Coordination Task", "Code Review", "Other"]


class Todo(BaseModel):
    who: str = Field(
        description="Who is responsible for this todo", min_length=1, max_length=100
    )
    what: str
    when: date
    criticality: Criticality
    theme: TodoTheme


class MeetingTodos(BaseModel):
    todos: list[Todo]
    meeting_date: date
    attendees: list[str]


def load_transcript(transcript: str) -> str:
    with open(transcript, "r") as f:
        return f.read()


transcript1 = load_transcript("src/oreilly_edd_course/transcript1.txt")
transcript2 = load_transcript("src/oreilly_edd_course/transcript2.txt")
transcript3 = load_transcript("src/oreilly_edd_course/transcript3.txt")


# async def extract_todos(transcript: str) -> MeetingTodos:
#     agent = Agent(
#         model,
#         instructions="""
#         Get Todos from Meeting notes. There should be an atomic single task per todo.
#         """,
#         output_type=MeetingTodos,
#         retries=3,
#     )
#
#     loaded_transcript = load_transcript(transcript)
#     result = await agent.run_sync(loaded_transcript)
#     assert isinstance(result, MeetingTodos)
#     return result


async def extract_todos(transcript: str) -> MeetingTodos:
    todo_agent = Agent(
        model=model,
        instructions="""
    You are a task-oriented assistant that can extract todos from a transcript.
    """,
        output_type=MeetingTodos,
        retries=4,
    )
    todos = await todo_agent.run(transcript)
    return todos.output


rubric = """
- TODOs should be clear and concise.
- TODOs should be actionable.
- TODOs should be assigned to a specific person.
"""
pydantic_llmjudge = LLMJudge(
    model=model,
    rubric=rubric,
)


dataset = Dataset(
    cases=[
        Case(name="Stand up meeting", inputs=transcript1),
        Case(
            name="Product Planning Meeting",
            inputs=transcript2,
        ),
        Case(
            name="Client Onboarding Call ",
            inputs=transcript3,
        ),
    ],
    evaluators=[pydantic_llmjudge],
)


async def evaluate():
    report = await dataset.evaluate(extract_todos)

    report.print(include_input=True, include_output=True, include_reasons=True)


if __name__ == "__main__":
    asyncio.run(evaluate())

# result = main("src/oreilly_edd_course/transcript1.txt")
#
# print(result)

# assert all(todo.who for todo in result.todos)

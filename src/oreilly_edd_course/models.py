"""The extractor's output. The schema is the first eval: the agent retries until it validates."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class Todo(BaseModel):
    who: str = Field(description="Full name of the person responsible", min_length=1)
    what: str = Field(description="The action to take, understandable on its own")
    when: date = Field(description="Due date")
    criticality: Literal["high", "medium", "low"]


class MeetingTodos(BaseModel):
    todos: list[Todo]
    meeting_date: date
    attendees: list[str] = Field(description="Full names of everyone who spoke")

    @field_validator("meeting_date")
    @classmethod
    def meeting_date_is_plausible(cls, v: date) -> date:
        assert date(2020, 1, 1) <= v <= date(2030, 1, 1), (
            f"{v} is not a plausible meeting date"
        )
        return v

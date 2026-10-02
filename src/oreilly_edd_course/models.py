"""The extractor's output. The schema is the first eval: the agent retries until it validates."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class Todo(BaseModel):
    who: str = Field(description="Full name of the person responsible", min_length=1)
    what: str = Field(description="The action to take, understandable on its own")
    when: date = Field(description="Due date")
    criticality: Literal["high", "medium", "low"]


class MeetingTodos(BaseModel):
    todos: list[Todo]
    meeting_date: date
    attendees: list[str] = Field(description="Full names of everyone who spoke")

    @model_validator(mode="after")
    def validate_todo_dates(self) -> "MeetingTodos":
        for todo in self.todos:
            if todo.when < self.meeting_date:
                raise ValueError(
                    f"The due date for '{todo.what}' ({todo.when}) cannot be before the meeting date ({self.meeting_date})."
                )
        return self

    @field_validator("meeting_date")
    @classmethod
    def meeting_date_is_plausible(cls, v: date) -> date:
        if not (date(2020, 1, 1) <= v <= date(2030, 1, 1)):
            raise ValueError(
                f"{v} is not a plausible meeting date, please use meeting data between 2020 and 2030"
            )
        return v

from datetime import date

from pydantic import BaseModel, EmailStr, Field, field_validator


class Person(BaseModel):
    """Person schema."""

    name: str
    email: EmailStr | None = None


class ActionItem(BaseModel):
    """Action item schema."""

    task: str = Field(min_length=1)
    owner: Person
    when: date


class ActionItems(BaseModel):
    """Action items schema."""

    action_items: list[ActionItem]
    meeting_date: date
    attendees: list[Person]

    @field_validator("meeting_date")
    @classmethod
    def validate_meeting_date(cls, v: date) -> date:
        if v < date(2020, 1, 1):
            raise ValueError("Meeting date seems unreasonably old")
        return v

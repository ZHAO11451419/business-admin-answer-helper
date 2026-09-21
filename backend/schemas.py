from typing import Literal
from pydantic import BaseModel, Field, field_validator


Role = Literal["user", "assistant"]
Rating = Literal["positive", "negative"]


class HistoryMessage(BaseModel):
    role: Role
    content: str = Field(min_length=1, max_length=12000)


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=16, max_length=128)
    message: str = Field(min_length=1, max_length=6000)
    course: str = Field(default="General Business", max_length=100)
    question_type: str = Field(default="General", max_length=100)
    language: str = Field(default="English", max_length=40)
    detail: Literal["concise", "standard", "detailed"] = "standard"
    history: list[HistoryMessage] = Field(default_factory=list, max_length=8)
    store_content: bool = False

    @field_validator("message")
    @classmethod
    def clean_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("message cannot be empty")
        return value


class FeedbackRequest(BaseModel):
    session_id: str = Field(min_length=16, max_length=128)
    message_id: str = Field(min_length=16, max_length=128)
    rating: Rating
    reason: str | None = Field(default=None, max_length=100)
    course: str | None = Field(default=None, max_length=100)
    question_type: str | None = Field(default=None, max_length=100)
    store_content: bool = False
    question_text: str | None = Field(default=None, max_length=6000)
    answer_text: str | None = Field(default=None, max_length=20000)

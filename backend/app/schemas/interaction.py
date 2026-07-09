import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class InteractionBase(BaseModel):
    hcp_id: uuid.UUID
    interaction_type: str = "Meeting"
    occurred_at: datetime
    attendees: list[str] = Field(default_factory=list)
    topics_discussed: str = ""
    materials_shared: list[str] = Field(default_factory=list)
    samples_distributed: list[str] = Field(default_factory=list)
    sentiment: Literal["Positive", "Neutral", "Negative"] = "Neutral"
    outcomes: str = ""
    follow_up_actions: str = ""


class InteractionCreate(InteractionBase):
    source: Literal["form", "chat"] = "form"


class InteractionUpdate(BaseModel):
    interaction_type: str | None = None
    occurred_at: datetime | None = None
    attendees: list[str] | None = None
    topics_discussed: str | None = None
    materials_shared: list[str] | None = None
    samples_distributed: list[str] | None = None
    sentiment: Literal["Positive", "Neutral", "Negative"] | None = None
    outcomes: str | None = None
    follow_up_actions: str | None = None


class InteractionOut(InteractionBase):
    id: uuid.UUID
    hcp_name: str | None = None
    suggested_follow_ups: list[str] = Field(default_factory=list)
    adverse_events: list[dict] = Field(default_factory=list)
    adverse_event_report: str = ""
    source: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChatRequest(BaseModel):
    message: str
    hcp_id: uuid.UUID | None = None
    thread_id: str = "default"


class ChatResponse(BaseModel):
    reply: str
    interaction: InteractionOut | None = None

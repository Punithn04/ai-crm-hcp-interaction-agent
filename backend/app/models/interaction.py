import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSON, UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hcp_id = Column(UUID(as_uuid=True), ForeignKey("hcps.id"), nullable=False)

    interaction_type = Column(String, nullable=False, default="Meeting")
    occurred_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    attendees = Column(ARRAY(String), default=list)
    topics_discussed = Column(Text, default="")
    materials_shared = Column(ARRAY(String), default=list)
    samples_distributed = Column(ARRAY(String), default=list)

    sentiment = Column(String, default="Neutral")  # Positive | Neutral | Negative
    outcomes = Column(Text, default="")
    follow_up_actions = Column(Text, default="")
    suggested_follow_ups = Column(JSON, default=list)

    source = Column(String, default="form")  # "form" or "chat"

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    hcp = relationship("HCP", back_populates="interactions")

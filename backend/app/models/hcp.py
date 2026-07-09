import uuid

from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class HCP(Base):
    __tablename__ = "hcps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    specialty = Column(String, nullable=True)
    institution = Column(String, nullable=True)

    interactions = relationship("Interaction", back_populates="hcp", cascade="all, delete-orphan")

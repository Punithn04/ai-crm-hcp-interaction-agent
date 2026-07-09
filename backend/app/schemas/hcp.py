import uuid

from pydantic import BaseModel


class HCPOut(BaseModel):
    id: uuid.UUID
    name: str
    specialty: str | None = None
    institution: str | None = None

    model_config = {"from_attributes": True}


class MaterialOut(BaseModel):
    id: uuid.UUID
    name: str
    kind: str

    model_config = {"from_attributes": True}

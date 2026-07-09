import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.interaction import InteractionCreate, InteractionOut, InteractionUpdate
from app.services import interactions as svc

router = APIRouter(prefix="/api/interactions", tags=["interactions"])


@router.get("", response_model=list[InteractionOut])
def list_interactions(hcp_id: uuid.UUID, db: Session = Depends(get_db)):
    return svc.list_interactions_for_hcp(db, hcp_id)


@router.post("", response_model=InteractionOut)
def create_interaction(payload: InteractionCreate, db: Session = Depends(get_db)):
    return svc.create_interaction(db, payload.model_dump())


@router.get("/{interaction_id}", response_model=InteractionOut)
def get_interaction(interaction_id: uuid.UUID, db: Session = Depends(get_db)):
    interaction = svc.get_interaction(db, interaction_id)
    if interaction is None:
        raise HTTPException(status_code=404, detail="Interaction not found")
    return interaction


@router.patch("/{interaction_id}", response_model=InteractionOut)
def update_interaction(interaction_id: uuid.UUID, payload: InteractionUpdate, db: Session = Depends(get_db)):
    interaction = svc.update_interaction(db, interaction_id, payload.model_dump(exclude_unset=True))
    if interaction is None:
        raise HTTPException(status_code=404, detail="Interaction not found")
    return interaction


@router.delete("/{interaction_id}")
def delete_interaction(interaction_id: uuid.UUID, db: Session = Depends(get_db)):
    if not svc.delete_interaction(db, interaction_id):
        raise HTTPException(status_code=404, detail="Interaction not found")
    return {"ok": True}

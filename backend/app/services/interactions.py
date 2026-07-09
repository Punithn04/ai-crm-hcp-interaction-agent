import uuid

from sqlalchemy.orm import Session

from app.models.hcp import HCP
from app.models.interaction import Interaction


def create_interaction(db: Session, data: dict) -> Interaction:
    interaction = Interaction(**data)
    db.add(interaction)
    db.commit()
    db.refresh(interaction)
    return interaction


def update_interaction(db: Session, interaction_id: uuid.UUID, data: dict) -> Interaction | None:
    interaction = db.get(Interaction, interaction_id)
    if interaction is None:
        return None
    for field, value in data.items():
        if value is not None:
            setattr(interaction, field, value)
    db.commit()
    db.refresh(interaction)
    return interaction


def get_interaction(db: Session, interaction_id: uuid.UUID) -> Interaction | None:
    return db.get(Interaction, interaction_id)


def list_interactions_for_hcp(db: Session, hcp_id: uuid.UUID, limit: int = 10) -> list[Interaction]:
    return (
        db.query(Interaction)
        .filter(Interaction.hcp_id == hcp_id)
        .order_by(Interaction.occurred_at.desc())
        .limit(limit)
        .all()
    )


def find_hcp_by_name(db: Session, name: str) -> HCP | None:
    return db.query(HCP).filter(HCP.name.ilike(f"%{name}%")).first()


def delete_interaction(db: Session, interaction_id: uuid.UUID) -> bool:
    interaction = db.get(Interaction, interaction_id)
    if interaction is None:
        return False
    db.delete(interaction)
    db.commit()
    return True

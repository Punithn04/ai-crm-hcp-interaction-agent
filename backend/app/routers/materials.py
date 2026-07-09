from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.material import Material
from app.schemas.hcp import MaterialOut

router = APIRouter(prefix="/api/materials", tags=["materials"])


@router.get("", response_model=list[MaterialOut])
def list_materials(
    kind: str | None = Query(default=None),
    q: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(Material)
    if kind:
        query = query.filter(Material.kind == kind)
    if q:
        query = query.filter(Material.name.ilike(f"%{q}%"))
    return query.order_by(Material.name).limit(20).all()

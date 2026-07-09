from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.hcp import HCP
from app.schemas.hcp import HCPOut

router = APIRouter(prefix="/api/hcps", tags=["hcps"])


@router.get("", response_model=list[HCPOut])
def list_hcps(q: str | None = Query(default=None), db: Session = Depends(get_db)):
    query = db.query(HCP)
    if q:
        query = query.filter(or_(HCP.name.ilike(f"%{q}%"), HCP.institution.ilike(f"%{q}%")))
    return query.order_by(HCP.name).limit(20).all()

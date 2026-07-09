from sqlalchemy.orm import Session

from app.models.material import Material


def search_materials(db: Session, query: str, kind: str | None = None, limit: int = 5) -> list[Material]:
    q = db.query(Material)
    if kind:
        q = q.filter(Material.kind == kind)
    if query:
        q = q.filter(Material.name.ilike(f"%{query}%"))
    return q.limit(limit).all()

"""Seed the database with sample HCPs and materials for local testing/demo purposes.

Run with: python -m app.seed
"""

from app.database import Base, SessionLocal, engine
from app.models.hcp import HCP
from app.models.material import Material


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(HCP).count() == 0:
            db.add_all(
                [
                    HCP(name="Dr. Priya Sharma", specialty="Oncology", institution="Apollo Hospitals"),
                    HCP(name="Dr. John Smith", specialty="Cardiology", institution="City General Hospital"),
                    HCP(name="Dr. Emily Chen", specialty="Endocrinology", institution="Metro Health Clinic"),
                ]
            )
        if db.query(Material).count() == 0:
            db.add_all(
                [
                    Material(name="OncoBoost Phase III PDF", kind="material"),
                    Material(name="Product X Efficacy Deck", kind="material"),
                    Material(name="Cardio Care Brochure", kind="material"),
                    Material(name="OncoBoost 50mg Sample Pack", kind="sample"),
                    Material(name="Product X Trial Sample", kind="sample"),
                ]
            )
        db.commit()
        print("Seed complete.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()

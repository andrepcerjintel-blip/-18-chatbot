from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

PERSONALITY_FIELDS = (
    "shyness",
    "extroversion",
    "initiative",
    "romanticism",
    "sexual_openness",
    "playfulness",
    "assertiveness",
    "affection",
)


def _range_constraint(field: str) -> CheckConstraint:
    return CheckConstraint(f"{field} >= 0 AND {field} <= 100", name=f"ck_personality_{field}_range")


class PersonalityProfile(Base):
    __tablename__ = "personality_profiles"
    __table_args__ = tuple(_range_constraint(f) for f in PERSONALITY_FIELDS)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    character_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("characters.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    preset: Mapped[str] = mapped_column(String(50), nullable=False, default="custom")

    shyness: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    extroversion: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    initiative: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    romanticism: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    sexual_openness: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    playfulness: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    assertiveness: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    affection: Mapped[int] = mapped_column(Integer, nullable=False, default=50)

    character: Mapped["Character"] = relationship(back_populates="personality")

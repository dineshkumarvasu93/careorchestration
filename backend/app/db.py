"""Optional Postgres persistence layer.

This module is only imported when ``DATABASE_URL`` is configured. It keeps the
SQLAlchemy dependency out of the default in-memory code path so the app (and the
test suite) can run with no database and no extra packages installed.
"""

from __future__ import annotations

import os

from sqlalchemy import String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.types import JSON


def _normalize_database_url(url: str) -> str:
    """Prefer the psycopg (v3) driver, which ships modern wheels."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


class Base(DeclarativeBase):
    pass


class RuleVersionRow(Base):
    __tablename__ = "rule_versions"

    version: Mapped[str] = mapped_column(String(128), primary_key=True)
    published_at_utc: Mapped[str] = mapped_column(String(64))
    # Full validated rule payload (portable JSON; JSONB on Postgres).
    payload: Mapped[dict] = mapped_column(JSON)


class ActiveRuleRow(Base):
    __tablename__ = "rule_active_state"

    # Single-row table: id is always 1.
    id: Mapped[int] = mapped_column(primary_key=True)
    active_version: Mapped[str] = mapped_column(String(128))


def build_session_factory() -> sessionmaker:
    database_url = _normalize_database_url(os.environ["DATABASE_URL"].strip())
    engine = create_engine(database_url, pool_pre_ping=True, future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


__all__ = [
    "ActiveRuleRow",
    "RuleVersionRow",
    "build_session_factory",
    "select",
]

"""SQLite and SQLAlchemy session management for persisted claims."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    """Base class for backend database models."""


_engine = None
_session_factory: sessionmaker[Session] | None = None


def configure_database(database_url: str | None = None) -> None:
    """Configure the database engine. Tests may supply an isolated SQLite URL."""
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    url = database_url or settings.database_url
    parsed_url = make_url(url)
    if parsed_url.drivername.startswith("sqlite") and parsed_url.database not in {None, ":memory:"}:
        Path(parsed_url.database).parent.mkdir(parents=True, exist_ok=True)
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    _engine = create_engine(url, connect_args=connect_args)
    _session_factory = sessionmaker(bind=_engine, autocommit=False, autoflush=False)


def get_engine():
    """Return the configured engine, creating it lazily."""
    if _engine is None:
        configure_database()
    return _engine


def init_db() -> None:
    """Create backend tables when the API or worker starts."""
    from app import models  # noqa: F401 - ensures model metadata is registered

    Base.metadata.create_all(bind=get_engine())


def get_session() -> Generator[Session, None, None]:
    """Yield an API request session and close it after use."""
    if _session_factory is None:
        configure_database()
    assert _session_factory is not None
    session = _session_factory()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Yield a transactional session for worker operations."""
    if _session_factory is None:
        configure_database()
    assert _session_factory is not None
    session = _session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

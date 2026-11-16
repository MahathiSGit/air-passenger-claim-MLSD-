"""Isolated SQLite setup for backend tests."""

from __future__ import annotations

import pytest

from app.database import Base, configure_database, get_engine, init_db


@pytest.fixture(autouse=True)
def isolated_database(tmp_path):
    """Use a fresh SQLite file so route and worker tests prove persistence safely."""
    database_url = f"sqlite:///{tmp_path / 'claims.db'}"
    configure_database(database_url)
    init_db()
    yield database_url
    Base.metadata.drop_all(bind=get_engine())

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, text


def fetch_all(db_path: Path, query: str, params: dict[str, object] | None = None) -> list[tuple[object, ...]]:
    engine = create_engine(f"sqlite:///{db_path}")
    try:
        with engine.connect() as connection:
            rows = connection.execute(text(query), params or {}).fetchall()
            return [tuple(row) for row in rows]
    finally:
        engine.dispose()


def fetch_scalar(db_path: Path, query: str, params: dict[str, object] | None = None) -> object:
    engine = create_engine(f"sqlite:///{db_path}")
    try:
        with engine.connect() as connection:
            return connection.execute(text(query), params or {}).scalar_one()
    finally:
        engine.dispose()

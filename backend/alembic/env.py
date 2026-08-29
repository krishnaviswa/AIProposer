"""Alembic environment. Target URL comes from app.config (DATABASE_URL), not
alembic.ini, so migrations and the app agree on the database. Supports both a
sync and an async driver URL."""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool
from sqlalchemy.engine import Connection, make_url
from sqlalchemy.ext.asyncio import create_async_engine

import app.models  # noqa: F401  - registers tables on Base.metadata
from app.config import get_settings
from app.database import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _url() -> str:
    return context.get_x_argument(as_dictionary=True).get("url") or get_settings().database_url


def _kwargs() -> dict:
    return {
        "target_metadata": target_metadata,
        "compare_type": True,
        "compare_server_default": True,
        "render_as_batch": True,  # SQLite-safe ALTERs
    }


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, **_kwargs())
    with context.begin_transaction():
        context.run_migrations()


async def _run_async(url: str) -> None:
    engine = create_async_engine(url, poolclass=pool.NullPool)
    try:
        async with engine.connect() as conn:
            await conn.run_sync(do_run_migrations)
    finally:
        await engine.dispose()


def _run_sync(url: str) -> None:
    engine = create_engine(url, poolclass=pool.NullPool)
    try:
        with engine.connect() as conn:
            do_run_migrations(conn)
    finally:
        engine.dispose()


def run() -> None:
    url = _url()
    if context.is_offline_mode():
        context.configure(url=url, literal_binds=True, dialect_opts={"paramstyle": "named"}, **_kwargs())
        with context.begin_transaction():
            context.run_migrations()
    elif make_url(url).get_dialect().is_async:
        asyncio.run(_run_async(url))
    else:
        _run_sync(url)


run()

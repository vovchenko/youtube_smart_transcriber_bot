from __future__ import annotations

from typing import TYPE_CHECKING

import aiosqlite
import pytest

from bot.db import run_migrations, set_db_path

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from pathlib import Path


@pytest.fixture
async def db_path(tmp_path: Path) -> AsyncIterator[str]:
    path = f"{tmp_path}/test.db"
    set_db_path(path)
    await run_migrations(path)
    yield path


@pytest.fixture
async def db_conn(db_path: str) -> AsyncIterator[aiosqlite.Connection]:
    conn = await aiosqlite.connect(db_path)
    conn.row_factory = aiosqlite.Row
    try:
        yield conn
    finally:
        await conn.close()

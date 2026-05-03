from __future__ import annotations

import aiosqlite
import pytest

from bot.db import run_migrations


async def test_migrations_apply_cleanly(
    db_conn: aiosqlite.Connection,
) -> None:
    cursor = await db_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    tables = {row[0] for row in await cursor.fetchall()}
    expected = {
        "users", "usage_log", "subscriptions",
        "payments", "summary_cache", "schema_version",
    }
    assert expected.issubset(tables)


async def test_schema_version_recorded(
    db_conn: aiosqlite.Connection,
) -> None:
    cursor = await db_conn.execute(
        "SELECT version FROM schema_version ORDER BY version"
    )
    versions = [row[0] for row in await cursor.fetchall()]
    assert versions == [1, 2]


async def test_migrations_idempotent(db_path: str) -> None:
    await run_migrations(db_path)
    conn = await aiosqlite.connect(db_path)
    try:
        cursor = await conn.execute(
            "SELECT version FROM schema_version ORDER BY version"
        )
        versions = [row[0] for row in await cursor.fetchall()]
        assert versions == [1, 2]
    finally:
        await conn.close()


async def test_user_insert_and_read(
    db_conn: aiosqlite.Connection,
) -> None:
    await db_conn.execute(
        "INSERT INTO users (user_id, username, language_code) "
        "VALUES (?, ?, ?)",
        (12345, "testuser", "en"),
    )
    await db_conn.commit()
    cursor = await db_conn.execute(
        "SELECT username FROM users WHERE user_id = ?", (12345,)
    )
    row = await cursor.fetchone()
    assert row is not None
    assert row[0] == "testuser"


async def test_foreign_key_enforcement(
    db_conn: aiosqlite.Connection,
) -> None:
    await db_conn.execute("PRAGMA foreign_keys=ON")
    with pytest.raises(aiosqlite.IntegrityError):
        await db_conn.execute(
            "INSERT INTO usage_log "
            "(user_id, source_type, success) VALUES (?, ?, ?)",
            (99999, "youtube", 1),
        )

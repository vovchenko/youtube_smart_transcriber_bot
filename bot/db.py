from __future__ import annotations

import asyncio
import glob
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING

import aiosqlite
import structlog

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

logger: structlog.stdlib.BoundLogger = structlog.get_logger()

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"

_db_path: str = ""


def set_db_path(path: str) -> None:
    global _db_path
    _db_path = path


@asynccontextmanager
async def get_db() -> AsyncIterator[aiosqlite.Connection]:
    db = await aiosqlite.connect(_db_path)
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA busy_timeout=5000")
    await db.execute("PRAGMA foreign_keys=ON")
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()


async def run_migrations(db_path: str | None = None) -> None:
    path = db_path or _db_path
    if not path:
        msg = "Database path not configured"
        raise RuntimeError(msg)

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    db = await aiosqlite.connect(path)
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA busy_timeout=5000")
    await db.execute("PRAGMA foreign_keys=ON")

    try:
        await db.execute(
            "CREATE TABLE IF NOT EXISTS schema_version "
            "(version INTEGER PRIMARY KEY, "
            "applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
        )
        await db.commit()

        cursor = await db.execute(
            "SELECT version FROM schema_version ORDER BY version"
        )
        applied = {row[0] for row in await cursor.fetchall()}

        migration_files = sorted(glob.glob(str(MIGRATIONS_DIR / "*.sql")))

        for filepath in migration_files:
            filename = os.path.basename(filepath)
            version = int(filename.split("_")[0])

            if version in applied:
                continue

            with open(filepath) as f:
                sql = f.read()

            await logger.ainfo(
                "applying_migration", version=version, file=filename
            )
            await db.executescript(sql)
            await db.execute(
                "INSERT INTO schema_version (version) VALUES (?)",
                (version,),
            )
            await db.commit()
            await logger.ainfo("migration_applied", version=version)

    finally:
        await db.close()


async def migration_status(db_path: str | None = None) -> None:
    path = db_path or _db_path
    if not path:
        msg = "Database path not configured"
        raise RuntimeError(msg)

    if not os.path.exists(path):
        print(f"Database does not exist yet: {path}")
        return

    db = await aiosqlite.connect(path)
    try:
        cursor = await db.execute(
            "SELECT version, applied_at "
            "FROM schema_version ORDER BY version"
        )
        rows = await cursor.fetchall()

        if not rows:
            print("No migrations applied yet.")
            return

        print("Applied migrations:")
        for row in rows:
            print(f"  v{row[0]:03d} — applied at {row[1]}")
    finally:
        await db.close()


def cli() -> None:
    from bot.config import get_settings

    settings = get_settings()

    if len(sys.argv) < 2:
        print("Usage: python -m bot.db [migrate|status]")
        sys.exit(1)

    command = sys.argv[1]
    if command == "migrate":
        asyncio.run(run_migrations(settings.database_path))
    elif command == "status":
        asyncio.run(migration_status(settings.database_path))
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    cli()

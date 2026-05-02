from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram import Router
from aiogram.filters import Command

from bot.config import get_settings
from bot.db import get_db

if TYPE_CHECKING:
    from aiogram.types import Message

router = Router(name="admin")


@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    if not message.from_user:
        return

    settings = get_settings()
    if message.from_user.id != settings.admin_user_id:
        return

    async with get_db() as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        row = await cursor.fetchone()
        total_users: int = row[0] if row else 0

        cursor = await db.execute(
            "SELECT COUNT(*) FROM users "
            "WHERE first_seen_at >= datetime('now', '-1 day')"
        )
        row = await cursor.fetchone()
        new_users_24h: int = row[0] if row else 0

        cursor = await db.execute(
            "SELECT COUNT(*) FROM usage_log WHERE success = 1"
        )
        row = await cursor.fetchone()
        total_summaries: int = row[0] if row else 0

        cursor = await db.execute(
            "SELECT COUNT(*) FROM subscriptions "
            "WHERE expires_at > datetime('now')"
        )
        row = await cursor.fetchone()
        active_subs: int = row[0] if row else 0

        cursor = await db.execute(
            "SELECT created_at, user_id, error FROM usage_log "
            "WHERE success = 0 ORDER BY created_at DESC LIMIT 5"
        )
        errors = await cursor.fetchall()

    error_lines = ""
    if errors:
        error_lines = "\n\n<b>Last errors:</b>\n"
        for err in errors:
            error_lines += (
                f"\u2022 [{err[0]}] user {err[1]}: {err[2]}\n"
            )
    else:
        error_lines = "\n\nNo errors recorded."

    text = (
        "<b>Admin Dashboard</b>\n\n"
        f"Total users: {total_users}\n"
        f"New (24h): {new_users_24h}\n"
        f"Total summaries: {total_summaries}\n"
        f"Active subscriptions: {active_subs}"
        f"{error_lines}"
    )

    await message.answer(text, parse_mode="HTML")

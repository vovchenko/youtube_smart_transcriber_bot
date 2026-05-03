from __future__ import annotations

from datetime import UTC, datetime

from bot.config import get_settings
from bot.db import get_db


async def get_monthly_usage_count(user_id: int) -> int:
    """Return number of successful summaries this calendar month."""
    now = datetime.now(tz=UTC)
    month_start = now.replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )

    async with get_db() as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM usage_log "
            "WHERE user_id = ? AND success = 1 AND created_at >= ?",
            (user_id, month_start.isoformat()),
        )
        row = await cursor.fetchone()
        return int(row[0]) if row else 0


async def has_active_subscription(user_id: int) -> bool:
    """Check if the user has a non-expired subscription."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT 1 FROM subscriptions "
            "WHERE user_id = ? AND expires_at > datetime('now')",
            (user_id,),
        )
        return await cursor.fetchone() is not None


async def get_summary_credits(user_id: int) -> int:
    """Return the number of purchased single-summary credits."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT summary_credits FROM users WHERE user_id = ?", (user_id,)
        )
        row = await cursor.fetchone()
        return int(row[0]) if row else 0


async def will_use_credit(user_id: int) -> bool:
    """Return True if the next summary will consume a purchased credit, not free quota."""
    if await has_active_subscription(user_id):
        return False
    settings = get_settings()
    used = await get_monthly_usage_count(user_id)
    return used >= settings.free_quota_per_month


async def can_summarize(user_id: int) -> bool:
    """Return True if the user can request a summary."""
    if await has_active_subscription(user_id):
        return True

    settings = get_settings()
    used = await get_monthly_usage_count(user_id)
    if used < settings.free_quota_per_month:
        return True

    return await get_summary_credits(user_id) > 0


async def get_usage_summary(user_id: int) -> str:
    """Return a human-readable usage summary for /usage."""
    settings = get_settings()

    if await has_active_subscription(user_id):
        async with get_db() as db:
            cursor = await db.execute(
                "SELECT expires_at FROM subscriptions "
                "WHERE user_id = ? AND expires_at > datetime('now')",
                (user_id,),
            )
            row = await cursor.fetchone()
            expires = row[0] if row else "unknown"
        return (
            f"You have an active subscription until <b>{expires}</b>."
        )

    used = await get_monthly_usage_count(user_id)
    limit = settings.free_quota_per_month
    remaining = max(0, limit - used)
    return (
        f"You've used <b>{used}</b> of <b>{limit}</b> "
        f"free summaries this month.\n"
        f"Remaining: <b>{remaining}</b>\n\n"
        f"Want unlimited? Subscribe for "
        f"{settings.subscription_stars}\u2b50/month "
        f"or pay {settings.single_summary_stars}\u2b50 per summary."
    )

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from bot.db import get_db


async def process_successful_payment(
    user_id: int,
    payment_charge_id: str,
    invoice_payload: str,
    stars_amount: int,
) -> None:
    async with get_db() as db:
        await db.execute(
            "INSERT OR IGNORE INTO payments "
            "(user_id, payment_charge_id, invoice_payload, stars_amount) "
            "VALUES (?, ?, ?, ?)",
            (user_id, payment_charge_id, invoice_payload, stars_amount),
        )

        if invoice_payload == "subscription":
            now = datetime.now(tz=UTC)
            expires = now + timedelta(days=30)
            await db.execute(
                "INSERT INTO subscriptions "
                "(user_id, started_at, expires_at, payment_charge_id, stars_paid) "
                "VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(user_id) DO UPDATE SET "
                "started_at=excluded.started_at, "
                "expires_at=excluded.expires_at, "
                "payment_charge_id=excluded.payment_charge_id, "
                "stars_paid=excluded.stars_paid",
                (
                    user_id,
                    now.isoformat(),
                    expires.isoformat(),
                    payment_charge_id,
                    stars_amount,
                ),
            )
        elif invoice_payload == "single_summary":
            await db.execute(
                "UPDATE users SET summary_credits = summary_credits + 1 WHERE user_id = ?",
                (user_id,),
            )

        await db.commit()


async def deduct_summary_credit(user_id: int) -> None:
    async with get_db() as db:
        await db.execute(
            "UPDATE users SET summary_credits = MAX(0, summary_credits - 1) WHERE user_id = ?",
            (user_id,),
        )
        await db.commit()


async def process_refund(user_id: int, payment_charge_id: str) -> None:
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT invoice_payload FROM payments WHERE payment_charge_id = ?",
            (payment_charge_id,),
        )
        row = await cursor.fetchone()

        await db.execute(
            "UPDATE payments SET refunded = 1 WHERE payment_charge_id = ?",
            (payment_charge_id,),
        )

        if row:
            payload = str(row[0])
            if payload == "subscription":
                await db.execute(
                    "DELETE FROM subscriptions WHERE user_id = ?", (user_id,)
                )
            elif payload == "single_summary":
                await db.execute(
                    "UPDATE users SET summary_credits = MAX(0, summary_credits - 1) "
                    "WHERE user_id = ?",
                    (user_id,),
                )

        await db.commit()

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from aiogram import Bot, F, Router
from aiogram.types import LabeledPrice

from bot.config import get_settings
from bot.services.payments import process_successful_payment

if TYPE_CHECKING:
    from aiogram.types import CallbackQuery, Message, PreCheckoutQuery
    from structlog.stdlib import BoundLogger

router = Router(name="payments")

log: structlog.stdlib.BoundLogger = structlog.get_logger()


@router.callback_query(F.data == "buy_subscription")
async def cb_buy_subscription(callback: CallbackQuery, bot: Bot) -> None:
    await callback.answer()
    if not callback.from_user:
        return
    s = get_settings()
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title="Unlimited Summaries — 30 Days",
        description="Summarize any YouTube video, unlimited times, for 30 days.",
        payload="subscription",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label="Monthly subscription", amount=s.subscription_stars)],
    )


@router.callback_query(F.data == "buy_single")
async def cb_buy_single(callback: CallbackQuery, bot: Bot) -> None:
    await callback.answer()
    if not callback.from_user:
        return
    s = get_settings()
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title="Single Summary",
        description="One AI summary for any YouTube video.",
        payload="single_summary",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label="Single summary", amount=s.single_summary_stars)],
    )


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery) -> None:
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment_handler(message: Message, log: BoundLogger) -> None:
    if not message.from_user or not message.successful_payment:
        return

    payment = message.successful_payment
    user_id = message.from_user.id

    await process_successful_payment(
        user_id=user_id,
        payment_charge_id=payment.telegram_payment_charge_id,
        invoice_payload=payment.invoice_payload,
        stars_amount=payment.total_amount,
    )

    await log.ainfo(
        "payment_received",
        user_id=user_id,
        payload=payment.invoice_payload,
        stars=payment.total_amount,
    )

    if payment.invoice_payload == "subscription":
        await message.answer(
            "Subscription activated! You have unlimited summaries for the next 30 days.\n"
            "Use /usage to check your status."
        )
    else:
        await message.answer(
            "Payment received! You have 1 summary credit.\n"
            "Send any YouTube link to use it."
        )

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="\ud83d\udcfa Try with example",
                    callback_data="try_example",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="\u2753 How it works",
                    callback_data="how_it_works",
                ),
            ],
        ]
    )


def payment_keyboard(subscription_stars: int, single_stars: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"Subscribe {subscription_stars}⭐/month",
                    callback_data="buy_subscription",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=f"Single summary {single_stars}⭐",
                    callback_data="buy_single",
                ),
            ],
        ]
    )


def confirm_delete_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Yes, delete everything",
                    callback_data="confirm_delete",
                ),
                InlineKeyboardButton(
                    text="Cancel",
                    callback_data="cancel_delete",
                ),
            ],
        ]
    )

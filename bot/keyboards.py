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

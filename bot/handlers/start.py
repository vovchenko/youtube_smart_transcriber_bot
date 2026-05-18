from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram import Router
from aiogram.filters import Command, CommandStart

from bot.db import get_db
from bot.keyboards import confirm_delete_keyboard, start_keyboard
from bot.services.quota import get_usage_summary
from bot.services.summarizer import SummarizationError, format_summary, summarize_transcript
from bot.services.transcript import (
    NoTranscriptAvailableError,
    ServiceBlockedError,
    TranscriptError,
    VideoNotAvailableError,
    fetch_youtube_transcript,
)

if TYPE_CHECKING:
    from aiogram.types import CallbackQuery, Message
    from structlog.stdlib import BoundLogger

_EXAMPLE_VIDEO_ID = "jNQXAC9IVRw"  # "Me at the zoo" — first YouTube video, 18 s

router = Router(name="start")

WELCOME_TEXT = (
    "Welcome to <b>YouTube AI Smart Transcriber</b>!\n\n"
    "Send me a YouTube link or an audio file, and I'll create "
    "a structured summary:\n"
    "\u2022 TL;DR\n"
    "\u2022 Key points with timestamps\n"
    "\u2022 Notable quotes\n"
    "\u2022 Actionable items\n\n"
    "You get <b>3 free summaries per month</b>. "
    "After that, 500\u2b50/month unlimited or 50\u2b50 per summary.\n\n"
    "Use /help for more details."
)

HELP_TEXT = (
    "<b>How to use this bot</b>\n\n"
    "1. Send a YouTube URL (any format)\n"
    "2. Or send an audio file (mp3, m4a, voice note)\n"
    "3. Wait ~30 seconds for your structured summary\n\n"
    "<b>What counts as a summary?</b>\n"
    "Each unique video or audio file = 1 summary. "
    "Re-requesting the same video uses the cache (free).\n\n"
    "<b>Free tier:</b> 3 summaries per calendar month\n"
    "<b>Subscription:</b> 500\u2b50/month for unlimited summaries\n"
    "<b>Pay-per-use:</b> 50\u2b50 per single summary\n\n"
    "Commands:\n"
    "/usage \u2014 check your quota\n"
    "/paysupport \u2014 payment help & refunds\n"
    "/delete_my_data \u2014 erase all your data"
)


async def _ensure_user(
    user_id: int, username: str | None, language_code: str | None
) -> None:
    async with get_db() as db:
        await db.execute(
            "INSERT OR IGNORE INTO users "
            "(user_id, username, language_code) VALUES (?, ?, ?)",
            (user_id, username, language_code),
        )
        await db.commit()


@router.message(CommandStart())
async def cmd_start(message: Message, log: BoundLogger) -> None:
    if not message.from_user:
        return
    await _ensure_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.language_code,
    )
    await log.ainfo("user_start", user_id=message.from_user.id)
    await message.answer(
        WELCOME_TEXT, parse_mode="HTML", reply_markup=start_keyboard()
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT, parse_mode="HTML")


@router.message(Command("usage"))
async def cmd_usage(message: Message) -> None:
    if not message.from_user:
        return
    summary = await get_usage_summary(message.from_user.id)
    await message.answer(summary, parse_mode="HTML")


@router.message(Command("paysupport"))
async def cmd_paysupport(message: Message) -> None:
    await message.answer(
        "For payment issues or refund requests, please contact "
        "the bot developer.\n"
        "Refunds are issued promptly upon request.",
        parse_mode="HTML",
    )


@router.message(Command("delete_my_data"))
async def cmd_delete_my_data(message: Message) -> None:
    await message.answer(
        "Are you sure you want to delete <b>all</b> your data?\n"
        "This includes your usage history, subscriptions, "
        "and payment records.\n\n"
        "This action cannot be undone.",
        parse_mode="HTML",
        reply_markup=confirm_delete_keyboard(),
    )


@router.callback_query(lambda c: c.data == "confirm_delete")
async def cb_confirm_delete(
    callback: CallbackQuery, log: BoundLogger
) -> None:
    if not callback.from_user or not callback.message:
        return

    user_id = callback.from_user.id
    async with get_db() as db:
        await db.execute(
            "DELETE FROM payments WHERE user_id = ?", (user_id,)
        )
        await db.execute(
            "DELETE FROM subscriptions WHERE user_id = ?", (user_id,)
        )
        await db.execute(
            "DELETE FROM usage_log WHERE user_id = ?", (user_id,)
        )
        await db.execute(
            "DELETE FROM users WHERE user_id = ?", (user_id,)
        )
        await db.commit()

    await log.ainfo("user_data_deleted", user_id=user_id)
    msg = callback.message
    if hasattr(msg, "edit_text"):
        await msg.edit_text("All your data has been deleted.")
    await callback.answer()


@router.callback_query(lambda c: c.data == "cancel_delete")
async def cb_cancel_delete(callback: CallbackQuery) -> None:
    msg = callback.message
    if msg and hasattr(msg, "edit_text"):
        await msg.edit_text("Data deletion cancelled.")
    await callback.answer()


@router.callback_query(lambda c: c.data == "try_example")
async def cb_try_example(callback: CallbackQuery) -> None:
    await callback.answer()
    if not callback.message:
        return

    status_msg = await callback.message.answer(
        f"⏳ Fetching transcript for example video…\n"
        f"(youtube.com/watch?v={_EXAMPLE_VIDEO_ID})"
    )

    try:
        result = await fetch_youtube_transcript(_EXAMPLE_VIDEO_ID)
        await status_msg.edit_text("🧠 Summarizing…")
        summary = await summarize_transcript(result)
        formatted = format_summary(summary, result.duration_seconds, _EXAMPLE_VIDEO_ID)
        await status_msg.edit_text(formatted, parse_mode="HTML")
    except NoTranscriptAvailableError:
        await status_msg.edit_text("❌ This example video has no captions.")
    except VideoNotAvailableError:
        await status_msg.edit_text("❌ Example video unavailable.")
    except (ServiceBlockedError, TranscriptError) as e:
        await status_msg.edit_text(f"❌ Could not fetch transcript: {e}")
    except SummarizationError as e:
        await status_msg.edit_text(f"❌ Could not summarize: {e}")


@router.callback_query(lambda c: c.data == "how_it_works")
async def cb_how_it_works(callback: CallbackQuery) -> None:
    if callback.message:
        await callback.message.answer(HELP_TEXT, parse_mode="HTML")
    await callback.answer()

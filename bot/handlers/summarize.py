from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from aiogram import F, Router

from bot.db import get_db
from bot.services.quota import can_summarize
from bot.services.transcript import (
    NoTranscriptAvailableError,
    ServiceBlockedError,
    TranscriptError,
    TranscriptResult,
    VideoNotAvailableError,
    extract_video_id,
    fetch_youtube_transcript,
)

if TYPE_CHECKING:
    from aiogram.types import Message
    from structlog.stdlib import BoundLogger

router = Router(name="summarize")

log: structlog.stdlib.BoundLogger = structlog.get_logger()

_TRANSCRIPT_PREVIEW_LIMIT = 4000


def _format_transcript(result: TranscriptResult) -> str:
    text = " ".join(s.text for s in result.segments)
    if len(text) > _TRANSCRIPT_PREVIEW_LIMIT:
        text = text[:_TRANSCRIPT_PREVIEW_LIMIT] + "…"
    mins, secs = divmod(result.duration_seconds, 60)
    header = f"<b>Transcript</b> ({mins}m {secs}s · {result.source})\n\n"
    return header + text


async def _ensure_user(message: Message) -> None:
    if not message.from_user:
        return
    async with get_db() as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username, language_code) VALUES (?, ?, ?)",
            (
                message.from_user.id,
                message.from_user.username,
                message.from_user.language_code,
            ),
        )
        await db.commit()


async def _log_usage(
    user_id: int,
    video_id: str,
    result: TranscriptResult | None,
    error: str | None,
) -> None:
    async with get_db() as db:
        await db.execute(
            "INSERT INTO usage_log "
            "(user_id, source_type, source_id, duration_seconds, success, error) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                user_id,
                "youtube",
                video_id,
                result.duration_seconds if result else None,
                0 if error else 1,
                error,
            ),
        )
        await db.commit()


@router.message(F.text)
async def handle_text(message: Message, log: BoundLogger) -> None:
    if not message.from_user or not message.text:
        return

    video_id = extract_video_id(message.text)
    if not video_id:
        await message.answer(
            "Send me a YouTube link or audio file to get a summary.\n"
            "Use /help for more details."
        )
        return

    user_id = message.from_user.id
    await _ensure_user(message)

    if not await can_summarize(user_id):
        await message.answer(
            "You've used all your free summaries this month.\n\n"
            "Subscribe for 500⭐/month or pay 50⭐ per summary.\n"
            "Use /usage to see your quota."
        )
        return

    status_msg = await message.answer("⏳ Fetching transcript…")

    result: TranscriptResult | None = None
    error_text: str | None = None

    try:
        result = await fetch_youtube_transcript(video_id)
    except NoTranscriptAvailableError:
        error_text = "This video has no captions available."
    except VideoNotAvailableError:
        error_text = "This video is unavailable or private."
    except ServiceBlockedError:
        error_text = "YouTube is temporarily blocking requests. Try again in a few minutes."
    except TranscriptError as e:
        error_text = f"Could not fetch transcript: {e}"
        await log.awarning("transcript_error", video_id=video_id, error=str(e))

    await _log_usage(user_id, video_id, result, error_text)

    if error_text:
        await status_msg.edit_text(f"❌ {error_text}")
        return

    if result:
        await status_msg.edit_text(_format_transcript(result), parse_mode="HTML")


@router.message(F.audio | F.voice | F.document)
async def handle_file(message: Message) -> None:
    await message.answer(
        "Audio file support is coming soon!\n"
        "For now, try sending a YouTube link.\n"
        "Use /help for more details."
    )

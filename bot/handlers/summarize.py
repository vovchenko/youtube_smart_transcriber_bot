from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from aiogram import F, Router

from bot.db import get_db
from bot.services.quota import can_summarize
from bot.services.summarizer import (
    SummarizationError,
    format_summary,
    summarize_transcript,
)
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


async def _get_cached_summary(video_id: str) -> str | None:
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT summary_text FROM summary_cache WHERE cache_key = ?", (video_id,)
        )
        row = await cursor.fetchone()
        if row:
            await db.execute(
                "UPDATE summary_cache SET hits = hits + 1 WHERE cache_key = ?", (video_id,)
            )
            await db.commit()
            return str(row[0])
    return None


async def _cache_summary(video_id: str, text: str) -> None:
    async with get_db() as db:
        await db.execute(
            "INSERT OR REPLACE INTO summary_cache (cache_key, summary_text) VALUES (?, ?)",
            (video_id, text),
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

    cached = await _get_cached_summary(video_id)
    if cached:
        await message.answer(cached, parse_mode="HTML")
        return

    if not await can_summarize(user_id):
        await message.answer(
            "You've used all your free summaries this month.\n\n"
            "Subscribe for 500⭐/month or pay 50⭐ per summary.\n"
            "Use /usage to see your quota."
        )
        return

    status_msg = await message.answer("⏳ Fetching transcript…")

    transcript_result: TranscriptResult | None = None
    error_text: str | None = None

    try:
        transcript_result = await fetch_youtube_transcript(video_id)
        await status_msg.edit_text("🧠 Summarizing…")
        summary = await summarize_transcript(transcript_result)
        formatted = format_summary(summary, transcript_result.duration_seconds)
        await _cache_summary(video_id, formatted)
        await status_msg.edit_text(formatted, parse_mode="HTML")
    except NoTranscriptAvailableError:
        error_text = "This video has no captions available."
    except VideoNotAvailableError:
        error_text = "This video is unavailable or private."
    except ServiceBlockedError:
        error_text = "YouTube is temporarily blocking requests. Try again in a few minutes."
    except TranscriptError as e:
        error_text = f"Could not fetch transcript: {e}"
        await log.awarning("transcript_error", video_id=video_id, error=str(e))
    except SummarizationError as e:
        error_text = f"Could not summarize: {e}"
        await log.awarning("summarization_error", video_id=video_id, error=str(e))

    await _log_usage(user_id, video_id, transcript_result, error_text)

    if error_text:
        await status_msg.edit_text(f"❌ {error_text}")


@router.message(F.audio | F.voice | F.document)
async def handle_file(message: Message) -> None:
    await message.answer(
        "Audio file support is coming soon!\n"
        "For now, try sending a YouTube link.\n"
        "Use /help for more details."
    )

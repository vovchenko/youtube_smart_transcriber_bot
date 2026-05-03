from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import anthropic
import structlog
from anthropic.types import TextBlock

from bot.config import get_settings

log: structlog.stdlib.BoundLogger = structlog.get_logger()

if TYPE_CHECKING:
    from bot.services.transcript import TranscriptResult


@dataclass
class Summary:
    tldr: str
    key_points: list[str]
    quotes: list[str]
    action_items: list[str]
    raw_text: str


class SummarizationError(Exception):
    pass


_SYSTEM_PROMPT = """\
You are an expert note-taker for video content.
Analyze the transcript and return ONLY a valid JSON object.
No markdown fences, no explanation, nothing else outside the JSON.

Schema:
{
  "tldr": "2-3 sentence summary of the main topic and key takeaways",
  "key_points": [{"timestamp": "MM:SS", "point": "concise insight or topic"}],
  "quotes": ["exact memorable quote from the transcript"],
  "action_items": ["specific actionable recommendation"]
}

Rules:
- key_points: 5-10 items, each with the nearest MM:SS timestamp from the transcript
- quotes: 2-5 verbatim quotes; return [] if none stand out
- action_items: concrete recommendations only; return [] if the video has none"""


def _format_transcript_for_claude(transcript: TranscriptResult) -> str:
    lines: list[str] = []
    for seg in transcript.segments:
        mins, secs = divmod(int(seg.start), 60)
        lines.append(f"[{mins:02d}:{secs:02d}] {seg.text}")
    return "\n".join(lines)


def format_summary(summary: Summary, duration_seconds: int) -> str:
    mins, secs = divmod(duration_seconds, 60)
    parts = [f"<b>TL;DR</b> ({mins}m {secs}s)\n{summary.tldr}"]

    if summary.key_points:
        points = "\n".join(f"• {p}" for p in summary.key_points)
        parts.append(f"<b>Key Points</b>\n{points}")

    if summary.quotes:
        quotes_text = "\n".join(f'"{q}"' for q in summary.quotes)
        parts.append(f"<b>Notable Quotes</b>\n{quotes_text}")

    if summary.action_items:
        items = "\n".join(f"• {a}" for a in summary.action_items)
        parts.append(f"<b>Action Items</b>\n{items}")

    return "\n\n".join(parts)


def _extract_json(raw: str) -> dict[str, Any]:
    text = raw.strip()
    # Strip markdown code fences if present (```json ... ``` or ``` ... ```)
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()
    parsed: Any = json.loads(text)
    if not isinstance(parsed, dict):
        raise TypeError(f"Expected JSON object, got {type(parsed).__name__}")
    return parsed


async def summarize_transcript(transcript: TranscriptResult) -> Summary:
    s = get_settings()
    if not s.anthropic_api_key:
        raise SummarizationError("ANTHROPIC_API_KEY is not configured")

    client = anthropic.AsyncAnthropic(api_key=s.anthropic_api_key)
    transcript_text = _format_transcript_for_claude(transcript)

    try:
        message = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2048,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": f"Transcript:\n\n{transcript_text}"}],
        )
    except anthropic.APIError as e:
        raise SummarizationError(f"Claude API error: {e}") from e

    # Find the first TextBlock (there may be thinking blocks before it)
    raw = ""
    for block in message.content:
        if isinstance(block, TextBlock) and block.text:
            raw = block.text
            break

    if not raw:
        await log.awarning(
            "claude_empty_response",
            stop_reason=message.stop_reason,
            content_types=[type(b).__name__ for b in message.content],
        )
        raise SummarizationError("Claude returned an empty response")

    try:
        data: dict[str, Any] = _extract_json(raw)
    except (json.JSONDecodeError, TypeError) as e:
        await log.awarning("claude_json_parse_error", raw=raw[:500], error=str(e))
        raise SummarizationError(f"Could not parse Claude response as JSON: {e}") from e

    key_points = [
        f"[{kp['timestamp']}] {kp['point']}"
        for kp in data.get("key_points", [])
        if isinstance(kp, dict)
    ]

    return Summary(
        tldr=str(data.get("tldr", "")),
        key_points=key_points,
        quotes=[str(q) for q in data.get("quotes", [])],
        action_items=[str(a) for a in data.get("action_items", [])],
        raw_text=raw,
    )

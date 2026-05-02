from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bot.services.transcript import TranscriptResult


@dataclass
class Summary:
    tldr: str
    key_points: list[str]
    quotes: list[str]
    action_items: list[str]
    raw_text: str


async def summarize_transcript(transcript: TranscriptResult) -> Summary:
    """Summarize a transcript using Claude Haiku. Day 3 implementation."""
    raise NotImplementedError("Day 3")

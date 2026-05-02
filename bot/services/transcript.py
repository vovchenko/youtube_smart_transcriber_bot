from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass

from youtube_transcript_api import (
    IpBlocked,
    NoTranscriptFound,
    RequestBlocked,
    TranscriptsDisabled,
    VideoUnavailable,
    YouTubeTranscriptApi,
    YouTubeTranscriptApiException,
)

_VIDEO_ID_RE = re.compile(
    r"(?:v=|youtu\.be/|embed/|shorts/|/v/)([a-zA-Z0-9_-]{11})"
)


def extract_video_id(text: str) -> str | None:
    m = _VIDEO_ID_RE.search(text)
    return m.group(1) if m else None


@dataclass
class TranscriptSegment:
    text: str
    start: float
    duration: float


@dataclass
class TranscriptResult:
    video_id: str
    title: str
    duration_seconds: int
    segments: list[TranscriptSegment]
    source: str


class TranscriptError(Exception):
    pass


class NoTranscriptAvailableError(TranscriptError):
    pass


class VideoNotAvailableError(TranscriptError):
    pass


class ServiceBlockedError(TranscriptError):
    pass


def _fetch_sync(video_id: str) -> TranscriptResult:
    try:
        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)

        try:
            transcript = transcript_list.find_transcript(["en"])
        except NoTranscriptFound:
            transcript = next(iter(transcript_list))

        fetched = transcript.fetch()
        segments = [
            TranscriptSegment(text=s.text, start=s.start, duration=s.duration)
            for s in fetched.snippets
        ]
        duration = int(sum(s.duration for s in fetched.snippets))
        source = f"{'generated' if fetched.is_generated else 'manual'}_{fetched.language_code}"

        return TranscriptResult(
            video_id=video_id,
            title="",
            duration_seconds=duration,
            segments=segments,
            source=source,
        )
    except (TranscriptsDisabled, NoTranscriptFound):
        raise NoTranscriptAvailableError(
            f"No captions available for video {video_id}"
        ) from None
    except VideoUnavailable as e:
        raise VideoNotAvailableError(str(e)) from e
    except (IpBlocked, RequestBlocked) as e:
        raise ServiceBlockedError(str(e)) from e
    except YouTubeTranscriptApiException as e:
        raise TranscriptError(str(e)) from e


async def fetch_youtube_transcript(video_id: str) -> TranscriptResult:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _fetch_sync, video_id)


async def transcribe_audio(file_path: str) -> TranscriptResult:
    raise NotImplementedError("Day 5")

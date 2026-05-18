from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from functools import partial

from bot.config import get_settings

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


def _poll_supadata_batch(client: object, job_id: str) -> object:
    import time
    from typing import Any

    from supadata.errors import SupadataError
    from supadata.types import Transcript

    c: Any = client
    for _ in range(30):  # up to 90 seconds
        time.sleep(3)
        try:
            response: dict[str, Any] = c._request("GET", f"/transcript/{job_id}")
        except SupadataError as e:
            raise TranscriptError(f"Supadata polling error: {e}") from e

        # Still processing — response contains job_id, status, or other in-progress markers
        if "job_id" in response or "status" in response:
            continue

        # Completed — response is a transcript payload
        if "content" in response:
            return Transcript(**response)

        raise TranscriptError(f"Unexpected polling response: {list(response.keys())}")

    raise TranscriptError("Timed out waiting for Supadata to process the video")


def _fetch_via_supadata(video_id: str) -> TranscriptResult:
    from typing import Any

    from supadata import Supadata
    from supadata.errors import SupadataError
    from supadata.types import BatchJob, Transcript, TranscriptChunk

    s = get_settings()
    client = Supadata(api_key=s.supadata_api_key)
    url = f"https://www.youtube.com/watch?v={video_id}"

    try:
        result: Any = client.transcript(url=url, lang="en")
    except SupadataError as e:
        code = e.error
        if code in ("transcript-unavailable", "no-transcript"):
            raise NoTranscriptAvailableError(e.details) from e
        if code in ("video-not-found", "video-unavailable"):
            raise VideoNotAvailableError(e.details) from e
        raise TranscriptError(str(e)) from e

    # Supadata returns BatchJob for longer videos — poll until done
    if isinstance(result, BatchJob):
        result = _poll_supadata_batch(client, result.job_id)

    if not isinstance(result, Transcript):
        raise TranscriptError(f"Unexpected response type from Supadata: {type(result).__name__}")

    chunks: list[TranscriptChunk] = (
        result.content if isinstance(result.content, list) else []
    )
    segments = [
        TranscriptSegment(
            text=c.text,
            start=c.offset / 1000.0,
            duration=c.duration / 1000.0,
        )
        for c in chunks
    ]
    duration = int(sum(c.duration for c in chunks) / 1000.0)
    source = f"supadata_{result.lang}"

    return TranscriptResult(
        video_id=video_id,
        title="",
        duration_seconds=duration,
        segments=segments,
        source=source,
    )


def _fetch_via_ytapi(video_id: str) -> TranscriptResult:
    from youtube_transcript_api import (
        IpBlocked,
        NoTranscriptFound,
        RequestBlocked,
        TranscriptsDisabled,
        VideoUnavailable,
        YouTubeTranscriptApi,
        YouTubeTranscriptApiException,
    )
    from youtube_transcript_api.proxies import GenericProxyConfig, WebshareProxyConfig

    s = get_settings()
    proxy_config: object | None = None
    if s.webshare_proxy_username and s.webshare_proxy_password:
        proxy_config = WebshareProxyConfig(
            proxy_username=s.webshare_proxy_username,
            proxy_password=s.webshare_proxy_password,
        )
    elif s.https_proxy:
        proxy_config = GenericProxyConfig(https_url=s.https_proxy)

    try:
        api = YouTubeTranscriptApi(proxy_config=proxy_config)  # type: ignore[arg-type]
        transcript_list = api.list(video_id)

        try:
            transcript = transcript_list.find_transcript(["en"])
        except NoTranscriptFound:
            transcript = next(iter(transcript_list))

        fetched = transcript.fetch()
        segments = [
            TranscriptSegment(text=seg.text, start=seg.start, duration=seg.duration)
            for seg in fetched.snippets
        ]
        duration = int(sum(seg.duration for seg in fetched.snippets))
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


def _fetch_sync(video_id: str) -> TranscriptResult:
    s = get_settings()
    if s.supadata_api_key:
        return _fetch_via_supadata(video_id)
    return _fetch_via_ytapi(video_id)


async def fetch_youtube_transcript(video_id: str) -> TranscriptResult:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(_fetch_sync, video_id))


async def transcribe_audio(file_path: str) -> TranscriptResult:
    raise NotImplementedError("Day 5")

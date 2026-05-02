# YouTube Smart Transcriber Bot

## Project status

**Day 1: COMPLETE** (built 2026-04-27)
**Next up: Day 2** — YouTube transcript extraction via `youtube-transcript-api`

### What's been built (Day 1)

- Full project structure with modular handlers and service layer
- Pydantic Settings v2 config loading from `.env`
- SQLite database with WAL mode, migration runner (`python -m bot.db migrate`)
- structlog logging (JSON in prod, colored in dev)
- Handlers: `/start`, `/help`, `/usage`, `/paysupport`, `/delete_my_data`, `/admin`
- `services/quota.py` — fully implemented (usage counting + subscription check)
- Service stubs with typed signatures: `transcript.py`, `summarizer.py`, `payments.py`
- Deploy artifacts: systemd unit, rsync deploy script
- 5 passing tests (migration apply, idempotency, schema version, CRUD, FK enforcement)
- `ruff check` and `mypy --strict` both pass clean

### Deviations from original spec

1. **Python 3.14** used instead of 3.11 (dev machine version) — pyproject.toml adjusted
2. **Relaxed dependency pins** (ranges like `aiogram>=3.15,<4` instead of exact pins) — exact pins from spec had conflicts with Python 3.14
3. **youtube-transcript-api 1.2.4** — version 0.6.3 from spec doesn't exist; library jumped from 0.6.2 to 1.2.x. The API surface changed significantly — Day 2 must use the new API
4. **`schema_version` table removed from `001_initial.sql`** — the migration runner in `db.py` creates it automatically via `CREATE TABLE IF NOT EXISTS`; having it in the SQL caused duplicate table errors

---

## What we're building

A Telegram bot (`@youtube_smart_transcriber_bot`) that:
1. Accepts a YouTube URL or audio file from the user
2. Extracts/transcribes the spoken content
3. Returns a structured summary: TL;DR + Key points with timestamps + Notable quotes + Actionable items
4. Charges via Telegram Stars (XTR) — 3 free summaries per month, then 500 stars/month unlimited or 50 stars per single summary

### Target audience

English-speaking knowledge workers — solo developers, founders, PMs, technical students.

### Why Telegram Stars (not Stripe)

Apple/Google policy requires digital goods/services in Telegram bots to use Stars only. We use `currency="XTR"` and empty `provider_token=""`.

---

## Tech stack

- Python 3.14
- aiogram 3.x (async Telegram framework)
- SQLite with WAL mode (no Postgres until 10K+ MAU)
- youtube-transcript-api 1.x (free, no API key)
- OpenAI gpt-4o-mini-transcribe ($0.003/min) as Whisper fallback
- Anthropic Claude Haiku 4.5 (`claude-haiku-4-5`) for summarization
- DigitalOcean droplet, systemd service
- Long polling (migrate to webhook on Day 6)

---

## Day-by-day roadmap

| Day | What gets built | Status |
|-----|-----------------|--------|
| 1 | Project foundation, deploy, /start handler, DB schema, config | **DONE** |
| 2 | YouTube transcript extraction via `youtube-transcript-api` | **NEXT** |
| 3 | Claude Haiku summarization with structured prompt | TODO |
| 4 | Telegram Stars payments — invoice, pre_checkout, successful_payment, subscription tracking | TODO |
| 5 | Audio file support — voice notes, mp3, m4a -> gpt-4o-mini-transcribe | TODO |
| 6 | Polish — rate limiting, /admin improvements, error tracking, migration to webhook | TODO |
| 7 | Launch — landing page, posts on Indie Hackers / Reddit / HN | TODO |

---

## Architecture

1. **Modular handler structure**: separate routers in `bot/handlers/` — `start`, `summarize`, `payments`, `admin`
2. **Service layer separation**: business logic in `bot/services/` — handlers are thin, services do the work
3. **Configuration via Pydantic Settings**: all config from `.env`, no hardcoded values
4. **Async everywhere**: `aiosqlite` for DB, `httpx.AsyncClient` for HTTP. No `requests` library
5. **Database migrations as plain SQL**: `migrations/001_initial.sql`, etc. Runner in `bot/db.py`
6. **Logging via structlog**: JSON in production, human-readable in dev. `user_id` as context var
7. **Type hints everywhere**: code passes `ruff check` and `mypy --strict`

---

## Project layout

```
bot/
  __main__.py          # Entry point: config -> logging -> migrations -> polling
  config.py            # Pydantic Settings v2 (loads .env)
  db.py                # aiosqlite connection, WAL mode, migration runner
  logging.py           # structlog setup (JSON prod / colored dev)
  keyboards.py         # Inline keyboards (start menu, delete confirmation)
  handlers/
    __init__.py        # get_root_router() aggregates all routers
    start.py           # /start, /help, /usage, /paysupport, /delete_my_data + callbacks
    admin.py           # /admin (admin-only stats dashboard)
    summarize.py       # Placeholder catch-all for text/file messages
    payments.py        # Empty router stub
  services/
    quota.py           # IMPLEMENTED: get_monthly_usage_count, has_active_subscription, can_summarize, get_usage_summary
    transcript.py      # STUB: TranscriptSegment, TranscriptResult, fetch_youtube_transcript, transcribe_audio
    summarizer.py      # STUB: Summary dataclass, summarize_transcript
    payments.py        # STUB: create_subscription_invoice, create_single_summary_invoice, process_successful_payment, process_refund
migrations/
  001_initial.sql      # Tables: users, usage_log, subscriptions, payments, summary_cache
deploy/
  youtube-smart-transcriber.service   # systemd unit (User=botuser)
  deploy.sh            # rsync + restart script (reads .env.deploy)
tests/
  conftest.py          # Fixtures: db_path (tmp), db_conn
  test_db.py           # 5 tests: migrations, schema_version, idempotency, CRUD, FK
```

---

## Day 2 instructions

### Goal
Implement YouTube transcript extraction in `bot/services/transcript.py` and wire it into `bot/handlers/summarize.py`.

### What to build

1. **`bot/services/transcript.py`** — replace stubs with real implementation:
   - `fetch_youtube_transcript(video_id: str) -> TranscriptResult` using `youtube-transcript-api` v1.x
   - Extract video ID from various YouTube URL formats (youtube.com/watch?v=, youtu.be/, shorts/, etc.)
   - Prefer English captions, fall back to auto-generated
   - IMPORTANT: the library API changed significantly in v1.x — read the actual installed package, don't rely on v0.6.x examples

2. **`bot/handlers/summarize.py`** — wire up the text handler:
   - Detect YouTube URLs in incoming messages (regex)
   - Extract video ID
   - Call `fetch_youtube_transcript`
   - For now (until Day 3), return the raw transcript text (truncated to 4096 chars for Telegram message limit)
   - Check quota via `services/quota.py` before processing
   - Log to `usage_log` table on success/failure

3. **Update the "Try with example" callback** in `bot/handlers/start.py` to actually process a hardcoded YouTube URL instead of saying "Coming on Day 2!"

### Key details
- `youtube-transcript-api` v1.2.4 is installed — its API differs from v0.6.x
- The `can_summarize()` function in `services/quota.py` is ready to use
- After transcript fetch, insert a row into `usage_log` via `get_db()`
- The `summary_cache` table uses `cache_key` — use the video_id as cache key for YouTube

### Dev workflow
```bash
cp .env.example .env   # fill in BOT_TOKEN + ADMIN_USER_ID
make install            # if deps not installed
make dev                # runs with watchfiles auto-reload
make lint               # ruff check + mypy --strict (must pass)
make test               # pytest (must pass)
```

---

## Commands reference

```bash
make install    # create venv, install deps
make dev        # run bot locally with auto-reload
make migrate    # apply pending migrations
make test       # pytest
make lint       # ruff check + mypy --strict
make format     # ruff format
make deploy     # rsync to droplet + restart
make logs       # tail remote journalctl
```

## BotFather setup (manual)

1. `/newbot` -> "YouTube AI Smart Transcriber" -> `youtube_smart_transcriber_bot`
2. Token -> `.env` as `BOT_TOKEN`
3. `/setdescription` -> "Get structured AI summaries of YouTube videos and audio files. TL;DR, key points with timestamps, notable quotes, and action items. 3 free summaries per month."
4. `/setabouttext` -> "AI-powered video & podcast summaries with timestamps. Free tier: 3/month."
5. Commands menu is set programmatically on bot startup

## Droplet first-time setup

```bash
sudo useradd -m -s /bin/bash botuser
sudo mkdir -p /opt/youtube-smart-transcriber
sudo chown botuser:botuser /opt/youtube-smart-transcriber
sudo cp deploy/youtube-smart-transcriber.service /etc/systemd/system/
sudo systemctl enable youtube-smart-transcriber
```

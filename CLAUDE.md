# YouTube Smart Transcriber Bot

## Project status

**Days 1–4: COMPLETE** (last updated 2026-05-03)
**Next up: Day 5** — Audio file support (voice notes, mp3, m4a → gpt-4o-mini-transcribe)

### What's been built

**Day 1** — Foundation
- Full project structure with modular handlers and service layer
- Pydantic Settings v2 config loading from `.env`
- SQLite database with WAL mode, migration runner (`python -m bot.db migrate`)
- structlog logging (JSON in prod, colored in dev)
- Handlers: `/start`, `/help`, `/usage`, `/paysupport`, `/delete_my_data`, `/admin`
- `services/quota.py` — usage counting, subscription check, credit check

**Day 2** — Transcript extraction
- `services/transcript.py` — Supadata as primary (handles cloud IPs), `youtube-transcript-api` as fallback
- `handlers/summarize.py` — YouTube URL detection, quota gate, usage logging
- Supadata batch job polling via `/transcript/{job_id}` (longer videos return async BatchJob)
- `start.py` "Try with example" callback wired to real transcript fetch

**Day 3** — Claude Haiku summarization
- `services/summarizer.py` — calls `claude-haiku-4-5-20251001`, returns structured JSON (TL;DR + Key Points + Quotes + Action Items)
- Summary cached in `summary_cache` table — re-requests are instant and free
- Status messages: "⏳ Fetching transcript…" → "🧠 Summarizing…" → result

**Day 4** — Telegram Stars payments
- `handlers/payments.py` — `buy_subscription` / `buy_single` callbacks, `pre_checkout_query`, `successful_payment`
- `services/payments.py` — records to `payments` table, activates subscription (30 days) or adds credit
- `migrations/002_add_summary_credits.sql` — `summary_credits` column on `users`
- `services/quota.py` — `can_summarize` checks credits; `will_use_credit` used to deduct on success
- Payment keyboard shown when quota exceeded
- Refund handling: removes subscription or decrements credit

### Deviations from original spec

1. **Supadata** used as primary transcript source (not `youtube-transcript-api` alone) — cloud/datacenter IPs are blocked by YouTube; Supadata handles this. Fallback to `youtube-transcript-api` when `SUPADATA_API_KEY` is not set.
2. **Python 3.13** used instead of 3.11 (dev machine version) — pyproject.toml adjusted
3. **Relaxed dependency pins** (ranges like `aiogram>=3.15,<4`) — exact pins conflicted with Python 3.13
4. **`schema_version` table** not in `001_initial.sql` — migration runner creates it automatically
5. **Model ID** `claude-haiku-4-5-20251001` (not `claude-haiku-4-5`) — must use full dated ID

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

- Python 3.13
- aiogram 3.x (async Telegram framework)
- SQLite with WAL mode (no Postgres until 10K+ MAU)
- Supadata API (primary transcript source, handles cloud IPs)
- youtube-transcript-api 1.x (fallback when SUPADATA_API_KEY not set)
- OpenAI gpt-4o-mini-transcribe ($0.003/min) — Day 5 audio transcription
- Anthropic Claude Haiku 4.5 (`claude-haiku-4-5-20251001`) for summarization
- Deployed on Railway with SQLite volume
- Long polling (migrate to webhook on Day 6)

---

## Day-by-day roadmap

| Day | What gets built | Status |
|-----|-----------------|--------|
| 1 | Project foundation, deploy, /start handler, DB schema, config | **DONE** |
| 2 | YouTube transcript extraction via Supadata + youtube-transcript-api fallback | **DONE** |
| 3 | Claude Haiku summarization with structured prompt + summary cache | **DONE** |
| 4 | Telegram Stars payments — invoice, pre_checkout, successful_payment, subscription + credits | **DONE** |
| 5 | Audio file support — voice notes, mp3, m4a -> gpt-4o-mini-transcribe | **NEXT** |
| 6 | Polish — rate limiting, /admin improvements, error tracking, migration to webhook | TODO |
| 7 | Launch — landing page, posts on Indie Hackers / Reddit / HN | TODO |

---

## Required environment variables

```
BOT_TOKEN=           # from @BotFather
ADMIN_USER_ID=       # your numeric Telegram user ID (from @userinfobot)
SUPADATA_API_KEY=    # from supadata.ai dashboard (required on cloud/Railway)
ANTHROPIC_API_KEY=   # from console.anthropic.com (required for summarization)
OPENAI_API_KEY=      # from platform.openai.com (required from Day 5)
DATABASE_PATH=./data/bot.db
ENVIRONMENT=development
```

Optional proxy fallback (only needed if not using Supadata):
```
WEBSHARE_PROXY_USERNAME=
WEBSHARE_PROXY_PASSWORD=
HTTPS_PROXY=
```

---

## Architecture

1. **Modular handler structure**: separate routers in `bot/handlers/` — `start`, `summarize`, `payments`, `admin`
2. **Service layer separation**: business logic in `bot/services/` — handlers are thin, services do the work
3. **Configuration via Pydantic Settings**: all config from `.env`, no hardcoded values
4. **Async everywhere**: `aiosqlite` for DB. Supadata/youtube-transcript-api run in thread executor (they use sync `requests`)
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
  keyboards.py         # Inline keyboards: start_keyboard, payment_keyboard, confirm_delete_keyboard
  handlers/
    __init__.py        # get_root_router() aggregates all routers
    start.py           # /start, /help, /usage, /paysupport, /delete_my_data + callbacks
    admin.py           # /admin (admin-only stats dashboard)
    summarize.py       # Text/file message handler — URL detection, quota, transcript, summarize
    payments.py        # buy_subscription, buy_single, pre_checkout_query, successful_payment
  services/
    quota.py           # get_monthly_usage_count, has_active_subscription, can_summarize,
                       # get_summary_credits, will_use_credit, get_usage_summary
    transcript.py      # extract_video_id, fetch_youtube_transcript (Supadata + fallback)
                       # _poll_supadata_batch polls /transcript/{job_id}
    summarizer.py      # summarize_transcript (Claude Haiku), format_summary
    payments.py        # process_successful_payment, deduct_summary_credit, process_refund
migrations/
  001_initial.sql      # Tables: users, usage_log, subscriptions, payments, summary_cache
  002_add_summary_credits.sql  # ALTER TABLE users ADD COLUMN summary_credits INTEGER DEFAULT 0
tests/
  conftest.py          # Fixtures: db_path (tmp), db_conn
  test_db.py           # 5 tests: migrations [1,2], schema_version, idempotency, CRUD, FK
```

---

## Day 5 instructions

### Goal
Add audio file support: voice notes, mp3, m4a, and other audio formats → transcribe via OpenAI gpt-4o-mini → summarize with existing Claude pipeline.

### What to build

1. **`bot/services/transcript.py`** — implement `transcribe_audio(file_path: str) -> TranscriptResult`:
   - Use `openai.AsyncOpenAI` with `client.audio.transcriptions.create(model="gpt-4o-mini-transcribe", file=...)`
   - Return `TranscriptResult` with `source="whisper"`, empty segments (or word-level if available), duration from file metadata
   - Handle file size limit (OpenAI max 25MB)

2. **`bot/handlers/summarize.py`** — implement `handle_file`:
   - Accept `F.audio | F.voice | F.document` (filter documents to audio MIME types)
   - Download file via `bot.download(file_id)` to a temp path
   - Call `transcribe_audio`, then `summarize_transcript` (same pipeline as YouTube)
   - Log to `usage_log` with `source_type="audio"`
   - Check quota before processing (same flow as YouTube)

### Key details
- OpenAI file upload requires an actual file object, not a URL — download first, then send
- Voice messages are already in OGG/Opus format — OpenAI accepts them directly
- `OPENAI_API_KEY` must be set in `.env`
- Use `aiofiles` or write to `tempfile.NamedTemporaryFile` for the download

---

## Commands reference

```bash
make install    # create venv, install deps
make dev        # run bot locally with auto-reload
make migrate    # apply pending migrations
make test       # pytest (5 tests, all pass)
make lint       # ruff check + mypy --strict (must pass clean)
make format     # ruff format
```

## BotFather setup (manual, already done)

1. `/newbot` -> "YouTube AI Smart Transcriber" -> `youtube_smart_transcriber_bot`
2. Token -> `.env` as `BOT_TOKEN`
3. `/setdescription` -> "Get structured AI summaries of YouTube videos and audio files."
4. `/setabouttext` -> "AI-powered video & podcast summaries. Free tier: 3/month."

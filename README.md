# YouTube AI Smart Transcriber Bot

Telegram bot that creates structured AI summaries of YouTube videos and audio files. Accepts a link or file, returns TL;DR, key points with timestamps, notable quotes, and action items. Monetized via Telegram Stars.

## Quickstart (development)

```bash
make install
cp .env.example .env   # fill in BOT_TOKEN and ADMIN_USER_ID
make dev
```

## Quickstart (deployment)

```bash
cp .env.example .env.deploy   # fill in DROPLET_IP, DROPLET_USER
make deploy
```

## Project layout

| Directory     | Description                                  |
|---------------|----------------------------------------------|
| `bot/`        | Application code — config, handlers, services |
| `bot/handlers/` | Telegram command and message handlers       |
| `bot/services/` | Business logic (quota, transcript, summary) |
| `migrations/` | SQL migration files applied in order         |
| `deploy/`     | systemd unit file and deploy script          |
| `tests/`      | pytest test suite                            |

## Roadmap

| Day | What gets built                                            |
|-----|------------------------------------------------------------|
| 1   | Project foundation, deploy, /start, DB schema, config     |
| 2   | YouTube transcript extraction via youtube-transcript-api   |
| 3   | Claude Haiku summarization with structured prompt          |
| 4   | Telegram Stars payments — invoices, subscriptions          |
| 5   | Audio file support — voice notes, mp3, m4a via Whisper     |
| 6   | Polish — rate limiting, /admin, error tracking, webhooks   |
| 7   | Launch — landing page, posts                               |

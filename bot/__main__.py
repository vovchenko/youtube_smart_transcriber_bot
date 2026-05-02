from __future__ import annotations

import asyncio
import sys

import structlog
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from bot.config import get_settings
from bot.db import run_migrations, set_db_path
from bot.handlers import get_root_router
from bot.logging import setup_logging

logger: structlog.stdlib.BoundLogger = structlog.get_logger()

BOT_COMMANDS = [
    BotCommand(command="start", description="Start the bot"),
    BotCommand(command="help", description="How to use this bot"),
    BotCommand(command="usage", description="Check your free quota"),
    BotCommand(command="paysupport", description="Payment support"),
    BotCommand(command="delete_my_data", description="Delete all your data"),
]


async def _inject_logger(handler, event, data):  # type: ignore[no-untyped-def]
    user = data.get("event_from_user")
    log = logger.bind(user_id=user.id if user else None)
    data["log"] = log
    return await handler(event, data)


async def main() -> None:
    settings = get_settings()

    setup_logging(log_level=settings.log_level, production=settings.is_production)

    set_db_path(settings.database_path)
    await run_migrations(settings.database_path)
    await logger.ainfo("migrations_complete")

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher()
    dp.update.outer_middleware(_inject_logger)

    root_router = get_root_router()
    dp.include_router(root_router)

    await bot.set_my_commands(BOT_COMMANDS)
    await bot.delete_webhook(drop_pending_updates=True)

    await logger.ainfo("bot_starting", environment=settings.environment)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)

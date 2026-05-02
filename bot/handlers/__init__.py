from __future__ import annotations

from aiogram import Router

from bot.handlers.admin import router as admin_router
from bot.handlers.payments import router as payments_router
from bot.handlers.start import router as start_router
from bot.handlers.summarize import router as summarize_router


def get_root_router() -> Router:
    root = Router(name="root")
    root.include_router(start_router)
    root.include_router(admin_router)
    root.include_router(payments_router)
    root.include_router(summarize_router)
    return root

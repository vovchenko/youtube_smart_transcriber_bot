from __future__ import annotations


async def create_subscription_invoice(user_id: int) -> str:
    """Create a Telegram Stars invoice for monthly subscription. Day 4 implementation."""
    raise NotImplementedError("Day 4")


async def create_single_summary_invoice(user_id: int) -> str:
    """Create a Telegram Stars invoice for a single summary. Day 4 implementation."""
    raise NotImplementedError("Day 4")


async def process_successful_payment(
    user_id: int, payment_charge_id: str, invoice_payload: str, stars_amount: int
) -> None:
    """Record a successful payment and activate subscription/credit. Day 4 implementation."""
    raise NotImplementedError("Day 4")


async def process_refund(user_id: int, payment_charge_id: str) -> None:
    """Process a payment refund. Day 4 implementation."""
    raise NotImplementedError("Day 4")

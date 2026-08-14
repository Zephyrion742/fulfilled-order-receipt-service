from __future__ import annotations

from html import escape
from typing import Any

from .infrai_email import SentEmail
from .models import OrderUpdate, UpdateResult


class ReceiptWorkflow:
    def __init__(self, email: Any) -> None:
        self.email = email

    def apply(self, update: OrderUpdate) -> UpdateResult:
        if update.state != "fulfilled":
            return UpdateResult(update.order_id, update.state, False, None)

        amount = f"{update.total:.2f} {escape(update.currency)}"
        sent = self.email.send(
            to=update.customer_email,
            subject=f"Receipt for order {update.order_id}",
            html=(
                f"<h1>Receipt</h1><p>Hi {escape(update.customer_name)},</p>"
                f"<p>Order <strong>{escape(update.order_id)}</strong> is fulfilled.</p>"
                f"<p>Total paid: <strong>{amount}</strong></p>"
            ),
            idempotency_key=f"receipt:{update.order_id}:fulfilled",
        )
        return UpdateResult(update.order_id, update.state, True, sent.message_id)

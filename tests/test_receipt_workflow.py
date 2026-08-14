from decimal import Decimal

from commerce_receipts.infrai_email import SentEmail
from commerce_receipts.models import OrderState, OrderUpdate
from commerce_receipts.receipt_sender import ReceiptWorkflow


class RecordingEmail:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def send(self, **message: str) -> SentEmail:
        self.calls.append(message)
        return SentEmail("msg_test_1042", {})


def order(state: OrderState) -> OrderUpdate:
    return OrderUpdate(
        order_id="ORDER-1042",
        customer_email="buyer@example.com",
        customer_name="Ada",
        state=state,
        total=Decimal("49.00"),
        currency="USD",
    )


def test_receipt_waits_for_fulfillment_then_uses_stable_event_key() -> None:
    email = RecordingEmail()
    workflow = ReceiptWorkflow(email)

    paid = workflow.apply(order("paid"))
    fulfilled = workflow.apply(order("fulfilled"))

    assert paid.receipt_sent is False
    assert fulfilled.receipt_sent is True
    assert fulfilled.message_id == "msg_test_1042"
    assert len(email.calls) == 1
    assert email.calls[0]["idempotency_key"] == "receipt:ORDER-1042:fulfilled"
    assert "49.00 USD" in email.calls[0]["html"]

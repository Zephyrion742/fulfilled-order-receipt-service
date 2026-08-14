from __future__ import annotations

import os
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from commerce_receipts.infrai_email import InfraiEmailClient
from commerce_receipts.models import OrderUpdate
from commerce_receipts.receipt_sender import ReceiptWorkflow


recipient = os.environ.get("RECEIPT_TO")
if not recipient:
    raise SystemExit("RECEIPT_TO is required")

result = ReceiptWorkflow(InfraiEmailClient()).apply(
    OrderUpdate(
        order_id="DEMO-1042",
        customer_email=recipient,
        customer_name="Ada",
        state="fulfilled",
        total=Decimal("49.00"),
        currency="USD",
    )
)
print(result.to_dict())


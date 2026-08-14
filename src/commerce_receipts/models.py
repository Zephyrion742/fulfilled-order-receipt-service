from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Literal


OrderState = Literal["checkout", "paid", "fulfilled"]


@dataclass(frozen=True)
class OrderUpdate:
    order_id: str
    customer_email: str
    customer_name: str
    state: OrderState
    total: Decimal
    currency: str

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "OrderUpdate":
        required = {
            "order_id",
            "customer_email",
            "customer_name",
            "state",
            "total",
            "currency",
        }
        missing = required - value.keys()
        unknown = value.keys() - required
        if missing:
            raise ValueError(f"missing fields: {', '.join(sorted(missing))}")
        if unknown:
            raise ValueError(f"unknown fields: {', '.join(sorted(unknown))}")
        if value["state"] not in {"checkout", "paid", "fulfilled"}:
            raise ValueError("state must be checkout, paid, or fulfilled")
        try:
            total = Decimal(str(value["total"]))
        except InvalidOperation as exc:
            raise ValueError("total must be a decimal amount") from exc
        if total < 0:
            raise ValueError("total must not be negative")
        return cls(
            order_id=str(value["order_id"]),
            customer_email=str(value["customer_email"]),
            customer_name=str(value["customer_name"]),
            state=value["state"],
            total=total,
            currency=str(value["currency"]).upper(),
        )


@dataclass(frozen=True)
class UpdateResult:
    order_id: str
    state: OrderState
    receipt_sent: bool
    message_id: str | None

    def to_dict(self) -> dict[str, str | bool | None]:
        return {
            "order_id": self.order_id,
            "state": self.state,
            "receipt_sent": self.receipt_sent,
            "message_id": self.message_id,
        }


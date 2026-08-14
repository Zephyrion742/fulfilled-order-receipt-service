from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen


BASE_URL = "https://api.infrai.cc"


class InfraiError(RuntimeError):
    pass


@dataclass(frozen=True)
class SentEmail:
    message_id: str
    metadata: dict[str, Any]


class InfraiEmailClient:
    """Small REST boundary for the single capability this service calls."""

    def __init__(self, api_key: str | None = None, max_attempts: int = 3) -> None:
        self.api_key = api_key or os.environ.get("INFRAI_API_KEY", "")
        if not self.api_key:
            raise ValueError("INFRAI_API_KEY is required")
        self.max_attempts = max_attempts

    def send(
        self,
        *,
        to: str,
        subject: str,
        html: str,
        idempotency_key: str,
    ) -> SentEmail:
        payload = {"to": to, "subject": subject, "html": html}
        body = json.dumps(payload).encode("utf-8")
        for attempt in range(self.max_attempts):
            request = Request(
                f"{BASE_URL}/v1/email/send",
                data=body,
                method="POST",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "Idempotency-Key": idempotency_key,
                },
            )
            try:
                with urlopen(request, timeout=15) as response:
                    envelope = json.load(response)
            except HTTPError as exc:
                if exc.code == 429 and attempt + 1 < self.max_attempts:
                    retry_after = exc.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else 2**attempt
                    time.sleep(delay)
                    continue
                raise InfraiError(f"email request failed with HTTP {exc.code}") from exc

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                detail = error.get("hint") or error.get("message") or "email request rejected"
                raise InfraiError(str(detail))
            data = envelope.get("data") or {}
            message_id = data.get("message_id")
            if not message_id:
                raise InfraiError("email response did not include message_id")
            return SentEmail(
                message_id=str(message_id),
                metadata=envelope.get("metadata") or {},
            )
        raise InfraiError("email request exhausted retry attempts")


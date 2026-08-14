from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .infrai_email import InfraiEmailClient
from .models import OrderUpdate
from .receipt_sender import ReceiptWorkflow


class ReceiptHandler(BaseHTTPRequestHandler):
    workflow: ReceiptWorkflow

    def do_POST(self) -> None:
        if self.path != "/order-updates":
            self._json(404, {"error": "route not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw: Any = json.loads(self.rfile.read(length))
            if not isinstance(raw, dict):
                raise ValueError("request body must be an object")
            result = self.workflow.apply(OrderUpdate.from_dict(raw))
            self._json(200, result.to_dict())
        except (ValueError, json.JSONDecodeError) as exc:
            self._json(400, {"error": str(exc)})

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        return


def serve(port: int) -> None:
    ReceiptHandler.workflow = ReceiptWorkflow(InfraiEmailClient())
    server = ThreadingHTTPServer(("127.0.0.1", port), ReceiptHandler)
    print(f"receipt service listening on http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    serve(args.port)


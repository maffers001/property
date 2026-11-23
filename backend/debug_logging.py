"""Request and SQLite timing logs to diagnose hangs / proxy resets.

Uses pure ASGI middleware (not BaseHTTPMiddleware) — Starlette's BaseHTTPMiddleware
is a known cause of connection resets / hung proxies under concurrent requests.
"""

from __future__ import annotations

import logging
import os
import time
import uuid

LOG = logging.getLogger("review_app")

SLOW_MS = float(os.environ.get("REVIEW_APP_SLOW_MS", "500"))


def configure_logging() -> None:
    level_name = (os.environ.get("REVIEW_APP_LOG_LEVEL") or "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(
            level=level,
            format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
            datefmt="%H:%M:%S",
        )
    else:
        root.setLevel(level)
    LOG.setLevel(level)
    logging.getLogger("property_pipeline.db").setLevel(level)
    LOG.info(
        "debug logging ready level=%s slow_ms=%.0f (ASGI timing middleware)",
        level_name,
        SLOW_MS,
    )


class RequestTimingMiddleware:
    """Log every /api request start + finish so hangs show as start without finish."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path") or ""
        if not path.startswith("/api"):
            await self.app(scope, receive, send)
            return

        req_id = uuid.uuid4().hex[:8]
        started = time.perf_counter()
        method = scope.get("method") or "?"
        qs = (scope.get("query_string") or b"").decode("latin-1")
        full = path + (("?" + qs) if qs else "")
        client = "?"
        if scope.get("client"):
            client = scope["client"][0]

        LOG.info("REQ start id=%s %s %s client=%s", req_id, method, full, client)

        status_holder = {"code": "?"}

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_holder["code"] = str(message.get("status", "?"))
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            elapsed_ms = (time.perf_counter() - started) * 1000
            LOG.exception(
                "REQ fail id=%s %s %s elapsed_ms=%.0f",
                req_id,
                method,
                path,
                elapsed_ms,
            )
            raise
        finally:
            elapsed_ms = (time.perf_counter() - started) * 1000
            slow = elapsed_ms >= SLOW_MS
            level = logging.WARNING if slow else logging.INFO
            LOG.log(
                level,
                "REQ done id=%s %s %s status=%s elapsed_ms=%.0f%s",
                req_id,
                method,
                path,
                status_holder["code"],
                elapsed_ms,
                " SLOW" if slow else "",
            )

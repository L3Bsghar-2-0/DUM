"""Real-time DUM -> IDP data forwarder.

Long-running process that pulls model data from the DUM FastAPI service
(default http://localhost:2400) and POSTs it as a single JSON document to
the IDP listener (default http://localhost:3000) on a fixed interval.

Run:
    python streamer.py

Env vars:
    DUM_URL              base URL of the DUM API           (default http://localhost:2400)
    IDP_URL              endpoint that receives the JSON   (default http://localhost:3000)
    STREAM_INTERVAL_SECS push cadence in seconds           (default 2.0)
    STREAM_TIMEOUT_SECS  per-request timeout               (default 10.0)
"""
from __future__ import annotations
import os
import sys
import time
import signal
import logging
from datetime import datetime, timezone
from typing import Any

import httpx

DUM_URL = os.getenv("DUM_URL", "http://localhost:2400").rstrip("/")
IDP_URL = os.getenv("IDP_URL", "http://localhost:3000").rstrip("/")
INTERVAL_SECS = float(os.getenv("STREAM_INTERVAL_SECS", "2"))
TIMEOUT_SECS = float(os.getenv("STREAM_TIMEOUT_SECS", "10"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [streamer] %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("streamer")

_running = True


def _stop(signum, frame):
    global _running
    log.info("signal %s received, shutting down", signum)
    _running = False


signal.signal(signal.SIGINT, _stop)
signal.signal(signal.SIGTERM, _stop)


def _safe_get(client: httpx.Client, path: str) -> Any:
    try:
        r = client.get(f"{DUM_URL}{path}", timeout=TIMEOUT_SECS)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log.warning("GET %s failed: %s", path, e)
        return None


def collect_snapshot(client: httpx.Client) -> dict:
    """Pulls current model state from DUM into a single JSON-serialisable dict."""
    return {
        "source": "dum",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "dum_url": DUM_URL,
        "records": _safe_get(client, "/records") or [],
        "summary": _safe_get(client, "/summary") or {},
        "forecast": _safe_get(client, "/forecast?hours=24") or [],
    }


def push(client: httpx.Client, payload: dict) -> bool:
    try:
        r = client.post(IDP_URL, json=payload, timeout=TIMEOUT_SECS)
        r.raise_for_status()
        return True
    except Exception as e:
        log.warning("POST %s failed: %s", IDP_URL, e)
        return False


def main() -> int:
    log.info("starting: DUM=%s -> IDP=%s every %.2fs", DUM_URL, IDP_URL, INTERVAL_SECS)
    with httpx.Client() as client:
        while _running:
            t0 = time.monotonic()
            payload = collect_snapshot(client)
            ok = push(client, payload)
            n = len(payload.get("records") or [])
            log.info("cycle: records=%d pushed=%s elapsed=%.2fs", n, ok, time.monotonic() - t0)
            # Sleep the remainder of the interval so cadence stays steady.
            sleep_for = max(0.0, INTERVAL_SECS - (time.monotonic() - t0))
            end = time.monotonic() + sleep_for
            while _running and time.monotonic() < end:
                time.sleep(min(0.2, end - time.monotonic()))
    log.info("stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env bash
# Aggregate local OpenDeepSeek health into one JSON object.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

TIMEOUT="${OPDS_HEALTH_TIMEOUT:-3}"
OPENWEBUI_URL="${OPDS_HEALTH_OPENWEBUI_URL:-http://127.0.0.1:3000/}"
BRIDGE_URL="${OPDS_HEALTH_BRIDGE_URL:-http://127.0.0.1:${OPDS_ARTIFACT_PORT:-8770}/health}"
HERMES_URL="${OPDS_HEALTH_HERMES_URL:-http://127.0.0.1:8642/health}"
ARTIFACTS_URL="${OPDS_HEALTH_ARTIFACTS_URL:-http://127.0.0.1:${OPDS_ARTIFACT_PORT:-8770}/artifacts}"

python3 - "$TIMEOUT" "$OPENWEBUI_URL" "$BRIDGE_URL" "$HERMES_URL" "$ARTIFACTS_URL" <<'PY'
import datetime as dt
import json
import sys
import time
import urllib.error
import urllib.request

timeout = float(sys.argv[1])
checks = [
    ("openwebui", sys.argv[2], True),
    ("bridge", sys.argv[3], True),
    ("hermes", sys.argv[4], True),
    ("artifacts", sys.argv[5], False),
]


def probe(url: str) -> dict:
    started = time.perf_counter()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "OpenDeepSeek-health-check"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(240).decode("utf-8", errors="replace")
            elapsed = round((time.perf_counter() - started) * 1000, 1)
            ok = 200 <= resp.status < 400
            return {
                "status": "ok" if ok else "down",
                "http_status": resp.status,
                "latency_ms": elapsed,
                "body_sample": body,
            }
    except urllib.error.HTTPError as exc:
        elapsed = round((time.perf_counter() - started) * 1000, 1)
        return {
            "status": "down",
            "http_status": exc.code,
            "latency_ms": elapsed,
            "error": str(exc)[:240],
        }
    except Exception as exc:  # noqa: BLE001
        elapsed = round((time.perf_counter() - started) * 1000, 1)
        return {
            "status": "down",
            "http_status": 0,
            "latency_ms": elapsed,
            "error": f"{type(exc).__name__}: {exc}"[:240],
        }


services = {}
required_ok = True
for name, url, required in checks:
    result = probe(url)
    result["url"] = url
    result["required"] = required
    services[name] = result
    if required and result["status"] != "ok":
        required_ok = False

payload = {
    "overall": "ok" if required_ok else "degraded",
    "timestamp": dt.datetime.now(dt.UTC).isoformat(),
    "services": services,
}
print(json.dumps(payload, ensure_ascii=False, indent=2))
raise SystemExit(0 if required_ok else 1)
PY

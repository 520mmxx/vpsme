#!/usr/bin/env python3
"""Read-only publish/first-run validator for OpenDeepSeek."""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"


def read_env() -> dict[str, str]:
    values: dict[str, str] = {}
    if not ENV_FILE.exists():
        return values
    for raw in ENV_FILE.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("\"'")
    values.update({k: v for k, v in os.environ.items() if k.startswith(("OPDS_", "HERMES_", "WEBUI_", "DEFAULT_", "DEEPSEEK_", "CUSTOM_MODEL_"))})
    return values


class Reporter:
    def __init__(self) -> None:
        self.errors = 0
        self.warnings = 0

    def ok(self, msg: str) -> None:
        print(f"[OK]   {msg}")

    def warn(self, msg: str) -> None:
        self.warnings += 1
        print(f"[WARN] {msg}")

    def fail(self, msg: str) -> None:
        self.errors += 1
        print(f"[FAIL] {msg}")


def port_open(host: str, port: int, timeout: float = 0.6) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def run_quiet(cmd: list[str]) -> tuple[int, str]:
    try:
        result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=30)
        return result.returncode, (result.stdout + result.stderr).strip()
    except Exception as exc:  # noqa: BLE001
        return 1, str(exc)


def main() -> int:
    env = read_env()
    r = Reporter()
    print("OpenDeepSeek config verify")
    print(f"  root: {ROOT}")
    print("")

    if ENV_FILE.exists():
        r.ok(".env exists")
    else:
        r.fail(".env missing. Run ./setup.sh --web or copy .env.example.")

    provider = env.get("OPDS_LLM_PROVIDER", "deepseek").strip().lower() or "deepseek"
    base_url = env.get("OPDS_LLM_BASE_URL") or env.get("DEEPSEEK_API_BASE", "https://api.deepseek.com")
    provider_key = env.get("OPDS_LLM_API_KEY") or env.get("DEEPSEEK_API_KEY", "")
    if provider == "deepseek":
        key = env.get("DEEPSEEK_API_KEY") or provider_key
        if key and key != "your-deepseek-api-key-here":
            r.ok("DeepSeek provider key is set")
        else:
            r.fail("DeepSeek provider selected but API key is missing or still placeholder")
        if "api.deepseek.com" in base_url:
            r.ok(f"DeepSeek base URL={base_url}")
        else:
            r.warn(f"DeepSeek provider uses non-default base URL={base_url}")
    elif provider == "custom":
        if base_url:
            r.ok(f"custom provider base URL={base_url}")
        else:
            r.fail("custom provider selected but OPDS_LLM_BASE_URL is missing")
        is_local = base_url.startswith(("http://localhost", "http://127.0.0.1", "http://host.docker.internal"))
        if provider_key and provider_key not in {"your-deepseek-api-key-here", "local"}:
            r.ok("custom provider key is set")
        elif is_local:
            r.ok("custom local provider may omit API key")
        else:
            r.fail("custom remote provider requires OPDS_LLM_API_KEY")
    else:
        r.fail(f"Unsupported OPDS_LLM_PROVIDER={provider}; use deepseek or custom")

    model = env.get("OPDS_LLM_MODEL") or env.get("DEFAULT_MODEL", "deepseek-v4-flash")
    if provider == "deepseek" and model in {"deepseek-v4-flash", "deepseek-v4-pro"}:
        r.ok(f"OPDS_LLM_MODEL={model}")
    elif provider == "deepseek" and model in {"deepseek-chat", "deepseek-reasoner"}:
        r.warn(f"{model} is a legacy compatibility alias; prefer deepseek-v4-flash/pro.")
    elif provider == "deepseek":
        r.fail(f"Unsupported DeepSeek model={model}")
    elif model:
        r.ok(f"custom provider model={model}")
    else:
        r.fail("custom provider model is missing")

    hermes_provider = env.get("HERMES_INFERENCE_PROVIDER", provider)
    expected_hermes_provider = "deepseek" if provider == "deepseek" else "custom"
    if hermes_provider == expected_hermes_provider:
        r.ok(f"HERMES_INFERENCE_PROVIDER={hermes_provider}")
    else:
        r.warn(f"HERMES_INFERENCE_PROVIDER={hermes_provider}; expected {expected_hermes_provider} for OPDS_LLM_PROVIDER={provider}")

    try:
        max_tokens = int(env.get("HERMES_AGENT_MAX_TOKENS", "32768"))
    except ValueError:
        max_tokens = 0
    if max_tokens >= 32768:
        r.ok(f"HERMES_AGENT_MAX_TOKENS={max_tokens}")
    else:
        r.fail("HERMES_AGENT_MAX_TOKENS must stay high (>=32768) for webpages/PPT/artifacts")

    host_dir = Path(env.get("HERMES_HOST_DIR", "agent-files")).expanduser()
    if host_dir.exists() and host_dir.is_dir():
        r.ok(f"HERMES_HOST_DIR exists: {host_dir}")
    else:
        r.warn(f"HERMES_HOST_DIR does not exist yet: {host_dir}")

    shared_memory = env.get("OPDS_SHARED_MEMORY_PATH", "/host/OpenDeepSeek-Memory/profile.md")
    if shared_memory.startswith("/host/"):
        r.ok(f"shared memory path is under /host: {shared_memory}")
    else:
        r.warn(f"shared memory path is outside /host: {shared_memory}")

    if shutil.which("docker"):
        r.ok("docker command found")
        code, output = run_quiet(["docker", "compose", "config", "-q"])
        if code == 0:
            r.ok("docker compose config validates")
        else:
            r.fail("docker compose config failed: " + output[:500])
    else:
        r.warn("docker command not found; install Docker Desktop before first run")

    for name, port in [("Open WebUI", 3000), ("Hermes", 8642), ("SearXNG", 8889)]:
        if port_open("127.0.0.1", port):
            r.ok(f"{name} port {port} is reachable")
        else:
            r.warn(f"{name} port {port} is not reachable now (service may be stopped)")

    code, output = run_quiet([
        "docker",
        "compose",
        "exec",
        "-T",
        "hermes-bridge",
        "python",
        "-c",
        "import urllib.request; urllib.request.urlopen('http://localhost:8765/health')",
    ])
    if code == 0:
        r.ok("Smart Bridge internal health is reachable")
    else:
        r.warn("Smart Bridge internal health is not reachable now: " + output[:240])

    if env.get("WEBUI_AUTH", "false").lower() == "false" and env.get("BIND_HOST", "127.0.0.1") == "0.0.0.0":
        r.fail("WEBUI_AUTH=false with BIND_HOST=0.0.0.0 is unsafe. Enable auth before exposing to network.")
    else:
        r.ok("network/auth setting is not the known unsafe public combination")

    print("")
    print(f"Result: {r.errors} error(s), {r.warnings} warning(s)")
    if r.warnings:
        print("Note: OpenWebUI may persist some settings in its database after first launch. This verifier does not mutate that DB; change those settings in Admin UI if needed.")
    return 1 if r.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

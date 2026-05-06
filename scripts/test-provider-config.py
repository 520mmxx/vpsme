#!/usr/bin/env python3
"""Offline regression tests for Provider configuration helpers."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "onboarding"))

from server import _provider_config  # noqa: E402


def expect_error(payload: dict[str, str]) -> None:
    try:
        _provider_config(payload)
    except ValueError:
        return
    raise AssertionError(f"expected ValueError for {payload}")


def main() -> int:
    deepseek = _provider_config({
        "provider": "deepseek",
        "api_key": "sk-test-123456",
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
    })
    assert deepseek["provider"] == "deepseek"
    assert deepseek["hermes_provider"] == "deepseek"
    assert deepseek["base_url"] == "https://api.deepseek.com"
    assert deepseek["model"] == "deepseek-v4-flash"

    local = _provider_config({
        "provider": "custom",
        "base_url": "http://host.docker.internal:11434/v1",
        "model": "qwen2.5-coder",
    })
    assert local["provider"] == "custom"
    assert local["hermes_provider"] == "custom"
    assert local["api_key"] == "local"
    assert local["base_url"] == "http://host.docker.internal:11434"

    remote = _provider_config({
        "provider": "custom",
        "api_key": "sk-remote-123456",
        "base_url": "https://openrouter.ai/api/v1",
        "model": "deepseek/deepseek-chat-v3.1",
    })
    assert remote["provider"] == "custom"
    assert remote["base_url"] == "https://openrouter.ai/api"
    assert remote["model"] == "deepseek/deepseek-chat-v3.1"

    expect_error({"provider": "deepseek", "model": "deepseek-v4-flash"})
    expect_error({"provider": "custom", "base_url": "http://example.com/v1", "model": "x"})
    expect_error({"provider": "custom", "base_url": "https://example.com/v1", "model": "x"})

    print("PASS: provider config helpers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

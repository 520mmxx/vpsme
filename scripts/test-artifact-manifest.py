#!/usr/bin/env python3
"""Offline test for Bridge Artifact Manifest generation."""

from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import tempfile


ROOT = pathlib.Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "bridge" / "hermes_image_bridge.py"


def load_bridge(host_root: pathlib.Path, output_root: pathlib.Path):
    os.environ["IMAGE_BRIDGE_HOST_ROOT"] = str(host_root)
    os.environ["IMAGE_BRIDGE_PUBLIC_HOST_PREFIX"] = "/host"
    os.environ["OPDS_ARTIFACT_ROOT"] = str(output_root)
    os.environ["OPDS_ARTIFACT_PUBLIC_BASE_URL"] = "http://localhost:8770"
    os.environ["OPDS_HOST_DISPLAY_PREFIX"] = "/Users/test/OpenDeepSeek-Agent"
    spec = importlib.util.spec_from_file_location("opds_bridge_artifact_test", BRIDGE)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load bridge module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        host_root = pathlib.Path(tmp) / "host"
        output_root = host_root / "OpenDeepSeek-Outputs"
        site = output_root / "site"
        site.mkdir(parents=True)
        (site / "index.html").write_text("<!doctype html><title>OpenDeepSeek</title>", encoding="utf-8")
        (site / ".env").write_text("SECRET=do-not-serve", encoding="utf-8")

        bridge = load_bridge(host_root, output_root)
        text = "已生成网站：/host/OpenDeepSeek-Outputs/site/index.html"
        updated = bridge.augment_assistant_text(text, "hermes", "artifact:test", "abc123")
        assert "OpenDeepSeek 产物卡片" in updated
        assert "index.html" in updated
        assert ".env" not in updated

        manifests = list((output_root / ".opendeepseek-artifacts").glob("*/manifest.json"))
        assert len(manifests) == 1
        manifest = json.loads(manifests[0].read_text(encoding="utf-8"))
        assert manifest["container_root"] == "/host/OpenDeepSeek-Outputs/site"
        assert manifest["local_root"] == "/Users/test/OpenDeepSeek-Agent/OpenDeepSeek-Outputs/site"
        assert manifest["files"][0]["path"] == "index.html"
        assert manifest["files"][0]["preview_url"].startswith("http://localhost:8770/artifacts/")
        assert all(item["path"] != ".env" for item in manifest["files"])

    print("PASS artifact manifest offline test")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""OpenDeepSeek read-only doctor/report tool."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from urllib.parse import urlparse
from urllib.error import HTTPError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"
SECRET_RE = re.compile(
    r"(?i)(api[_-]?key|secret|token|password|authorization|api_server_key|webui_secret_key)(=|:|\s+bearer\s+)([^\s\"']+)"
)


def redact(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        value = match.group(3)
        tail = value[-4:] if len(value) >= 8 else ""
        return f"{match.group(1)}{match.group(2)}***hidden***{tail}"

    text = SECRET_RE.sub(repl, text)
    text = re.sub(r"sk-[A-Za-z0-9_\-]{8,}", "sk-***hidden***", text)
    return text


def read_env() -> dict[str, str]:
    env: dict[str, str] = {}
    if not ENV_FILE.exists():
        return env
    for line in ENV_FILE.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        env[key.strip()] = value.strip().strip("\"'")
    return env


def write_env_updates(updates: dict[str, str]) -> None:
    original = ENV_FILE.read_text(encoding="utf-8", errors="replace").splitlines() if ENV_FILE.exists() else []
    seen: set[str] = set()
    output: list[str] = []
    for line in original:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key, _, _ = stripped.partition("=")
            name = key.strip()
            if name in updates:
                output.append(f"{name}={updates[name]}")
                seen.add(name)
                continue
        output.append(line)
    if output and output[-1].strip():
        output.append("")
    for key, value in updates.items():
        if key not in seen:
            output.append(f"{key}={value}")
    ENV_FILE.write_text("\n".join(output) + "\n", encoding="utf-8")


def safe_fix() -> int:
    env = read_env()
    if not ENV_FILE.exists():
        print(".env 不存在；请先运行 ./setup.sh --web 或复制 .env.example")
        return 1

    provider = env.get("OPDS_LLM_PROVIDER") or "deepseek"
    model = env.get("OPDS_LLM_MODEL") or env.get("DEFAULT_MODEL") or "deepseek-v4-flash"
    deepseek_key = env.get("DEEPSEEK_API_KEY", "")
    base_url = env.get("OPDS_LLM_BASE_URL") or env.get("DEEPSEEK_API_BASE") or "https://api.deepseek.com"
    api_key = env.get("OPDS_LLM_API_KEY") or deepseek_key
    updates = {
        "OPDS_LLM_PROVIDER": provider,
        "OPDS_LLM_BASE_URL": base_url,
        "OPDS_LLM_API_KEY": api_key,
        "OPDS_LLM_MODEL": model,
        "OPDS_LLM_PRO_MODEL": env.get("OPDS_LLM_PRO_MODEL") or "deepseek-v4-pro",
        "HERMES_INFERENCE_PROVIDER": env.get("HERMES_INFERENCE_PROVIDER") or ("deepseek" if provider == "deepseek" else "custom"),
        "ENABLE_LIGHTWEIGHT_ROUTING": env.get("ENABLE_LIGHTWEIGHT_ROUTING") or "true",
        "ENABLE_CHINA_MODE": "false",
        "ENABLE_RAG_WEB_SEARCH": "false",
        "ENABLE_CODE_INTERPRETER": "false",
        "ENABLE_RAG_HYBRID_SEARCH": "false",
        "HERMES_AGENT_MAX_TOKENS": env.get("HERMES_AGENT_MAX_TOKENS") or "32768",
        "OPDS_ARTIFACT_PORT": env.get("OPDS_ARTIFACT_PORT") or "8770",
        "OPDS_ARTIFACT_ROOT": env.get("OPDS_ARTIFACT_ROOT") or "/host/OpenDeepSeek-Outputs",
    }
    if provider == "deepseek":
        updates["DEEPSEEK_API_BASE"] = env.get("DEEPSEEK_API_BASE") or "https://api.deepseek.com"
    write_env_updates(updates)

    host_dir = Path(env.get("HERMES_HOST_DIR", str(ROOT / "agent-files"))).expanduser()
    for name in ["OpenDeepSeek-Inputs", "OpenDeepSeek-Outputs", "OpenDeepSeek-Memory"]:
        (host_dir / name).mkdir(parents=True, exist_ok=True)
    print("已完成安全修复：补齐 Provider 变量、切回轻量启动配置，并创建 OpenDeepSeek 输入/输出/记忆目录。")
    print("没有删除 volume，没有启动容器，没有修改公网暴露设置。")
    return 0


def run(cmd: list[str], timeout: int = 30) -> tuple[int, str]:
    try:
        result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
        return result.returncode, redact((result.stdout + result.stderr).strip())
    except FileNotFoundError:
        return 127, f"找不到命令：{cmd[0]}"
    except subprocess.TimeoutExpired:
        return 124, "命令超时"
    except Exception as exc:  # noqa: BLE001
        return 1, f"{type(exc).__name__}: {exc}"


def port_open(port: int, host: str = "127.0.0.1", timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def http_ok(url: str, timeout: float = 2.0) -> tuple[bool, str]:
    try:
        req = Request(url, headers={"User-Agent": "OpenDeepSeek-Doctor/1.0"})
        with urlopen(req, timeout=timeout) as resp:  # noqa: S310 - user/project-controlled diagnostics.
            return resp.status < 500, f"HTTP {resp.status}"
    except HTTPError as exc:
        return exc.code < 500, f"HTTP {exc.code}"
    except Exception as exc:  # noqa: BLE001
        return False, f"{type(exc).__name__}: {exc}"


class Doctor:
    def __init__(self, cn: bool = False) -> None:
        self.cn = cn
        self.env = read_env()
        self.items: list[dict[str, str]] = []

    def add(self, status: str, title: str, detail: str) -> None:
        self.items.append({"status": status, "title": title, "detail": detail})

    def check(self) -> None:
        self.check_system()
        self.check_env()
        self.check_ports()
        self.check_docker()
        self.check_services()
        self.check_host_write()
        if self.cn:
            self.check_cn_network()

    def check_system(self) -> None:
        self.add("ok", "项目目录", str(ROOT))
        code, out = run(["uname", "-a"], timeout=5)
        self.add("ok" if code == 0 else "warn", "系统信息", out[:240])
        try:
            pages = os.sysconf("SC_PHYS_PAGES")
            page_size = os.sysconf("SC_PAGE_SIZE")
            mem_gb = pages * page_size / 1024 / 1024 / 1024
            status = "ok" if mem_gb >= 6 else "warn"
            self.add(status, "可用内存级别", f"物理内存约 {mem_gb:.1f} GB；低内存建议只启动核心服务，不启用 full/SearXNG")
        except Exception:
            self.add("warn", "可用内存级别", "无法读取物理内存")

    def check_env(self) -> None:
        if ENV_FILE.exists():
            self.add("ok", ".env", "存在")
        else:
            self.add("error", ".env", "不存在；请运行 ./setup.sh --web 或复制 .env.example")
            return

        provider = self.env.get("OPDS_LLM_PROVIDER", "deepseek")
        base_url = self.env.get("OPDS_LLM_BASE_URL") or self.env.get("DEEPSEEK_API_BASE", "https://api.deepseek.com")
        model = self.env.get("OPDS_LLM_MODEL") or self.env.get("DEFAULT_MODEL", "deepseek-v4-flash")
        key = self.env.get("OPDS_LLM_API_KEY") or self.env.get("DEEPSEEK_API_KEY", "")
        self.add("ok", "Provider", f"{provider} · {model} · {base_url}")
        is_local = base_url.startswith(("http://localhost", "http://127.0.0.1", "http://host.docker.internal"))
        if key and key not in {"your-deepseek-api-key-here", "local"}:
            self.add("ok", "Provider Key", "已配置并脱敏")
        elif provider == "custom" and is_local:
            self.add("ok", "Provider Key", "本地自定义 API 可不填 Key")
        else:
            self.add("error", "Provider Key", "未配置或仍是占位符")

        if self.env.get("HERMES_AGENT_MAX_TOKENS", "32768").isdigit() and int(self.env.get("HERMES_AGENT_MAX_TOKENS", "32768")) >= 32768:
            self.add("ok", "Hermes 输出预算", f"HERMES_AGENT_MAX_TOKENS={self.env.get('HERMES_AGENT_MAX_TOKENS', '32768')}")
        else:
            self.add("error", "Hermes 输出预算", "不能低于 32768，网页/PPT/报告任务会被截断")

        if self.env.get("WEBUI_AUTH", "false").lower() == "false" and self.env.get("BIND_HOST", "127.0.0.1") == "0.0.0.0":
            self.add("error", "公网安全", "WEBUI_AUTH=false 且 BIND_HOST=0.0.0.0，不安全")
        else:
            self.add("ok", "公网安全", "未发现已知危险组合")

        if self.env.get("ENABLE_CHINA_MODE", "false").lower() == "true":
            self.add("warn", "启动配置", "ENABLE_CHINA_MODE=true 会默认启动 full profile/SearXNG；低内存电脑建议改为 false，按需运行 ./setup.sh start-full")
        if self.env.get("ENABLE_CODE_INTERPRETER", "false").lower() == "true":
            self.add("warn", "Open WebUI 负载", "ENABLE_CODE_INTERPRETER=true 会增加后台能力和资源占用；轻量发布默认建议 false")
        if self.env.get("ENABLE_RAG_HYBRID_SEARCH", "false").lower() == "true":
            self.add("warn", "RAG 负载", "ENABLE_RAG_HYBRID_SEARCH=true 可能触发 embedding/检索相关资源；轻量发布默认建议 false")

    def check_ports(self) -> None:
        for name, port in [("Open WebUI", 3000), ("Portal", 3001), ("Bridge Artifact", 8770), ("Hermes", 8642), ("SearXNG", 8889)]:
            self.add("ok" if port_open(port) else "warn", f"端口 {port}", f"{name} {'可连接' if port_open(port) else '未监听'}")

    def check_docker(self) -> None:
        if shutil.which("docker"):
            self.add("ok", "Docker 命令", "已安装")
        else:
            self.add("error", "Docker 命令", "未安装")
            return
        for title, cmd in [
            ("Docker 版本", ["docker", "--version"]),
            ("Compose 版本", ["docker", "compose", "version"]),
            ("Compose 配置", ["docker", "compose", "config", "-q"]),
            ("CN Compose 配置", ["docker", "compose", "-f", "docker-compose.cn.yml", "config", "-q"]),
        ]:
            code, out = run(cmd, timeout=20)
            self.add("ok" if code == 0 else "warn", title, out or "通过")

        code, out = run(["docker", "info"], timeout=8)
        self.add("ok" if code == 0 else "warn", "Docker daemon", "已运行" if code == 0 else out[:240])
        code, out = run(["docker", "compose", "ps"], timeout=12)
        self.add("ok" if code == 0 else "warn", "容器状态", out[:900] or "无输出")

    def check_services(self) -> None:
        for title, url in [
            ("Open WebUI", "http://localhost:3000"),
            ("Hermes", "http://localhost:8642/health"),
            ("Bridge", "http://localhost:8770/health"),
            ("SearXNG", "http://localhost:8889"),
        ]:
            ok, detail = http_ok(url, timeout=1.5)
            self.add("ok" if ok else "warn", title, f"{url} · {detail}")

        base = self.env.get("OPDS_LLM_BASE_URL") or self.env.get("DEEPSEEK_API_BASE", "https://api.deepseek.com")
        parsed = urlparse(base)
        if parsed.hostname in {"localhost", "127.0.0.1", "host.docker.internal"}:
            self.add("warn", "Provider 网络", "本地 Provider 需要启动对应本地服务后再测试")
        else:
            ok, detail = http_ok(base, timeout=3)
            self.add("ok" if ok else "warn", "Provider 网络", f"{base} · {detail}")

    def check_host_write(self) -> None:
        host_dir = Path(self.env.get("HERMES_HOST_DIR", str(ROOT / "agent-files"))).expanduser()
        try:
            target = host_dir / "OpenDeepSeek-Outputs" / ".doctor-write-test"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("ok\n", encoding="utf-8")
            target.unlink(missing_ok=True)
            self.add("ok", "/host 写入", f"可写：{target.parent}")
        except Exception as exc:  # noqa: BLE001
            self.add("error", "/host 写入", f"{type(exc).__name__}: {exc}")

    def check_cn_network(self) -> None:
        for title, url in [
            ("Gitee", "https://gitee.com"),
            ("GitCode", "https://gitcode.com"),
            ("DeepSeek API", "https://api.deepseek.com"),
            ("TUNA PyPI", "https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple"),
            ("npmmirror", "https://registry.npmmirror.com"),
        ]:
            ok, detail = http_ok(url, timeout=4)
            self.add("ok" if ok else "warn", f"国内网络：{title}", detail)

    def print(self) -> int:
        errors = sum(1 for item in self.items if item["status"] == "error")
        warnings = sum(1 for item in self.items if item["status"] == "warn")
        print("OpenDeepSeek Doctor")
        print(f"root: {ROOT}")
        print("")
        for item in self.items:
            prefix = {"ok": "[OK]  ", "warn": "[WARN]", "error": "[FAIL]"}[item["status"]]
            print(f"{prefix} {item['title']}: {item['detail']}")
        print("")
        print(f"Result: {errors} error(s), {warnings} warning(s)")
        return 1 if errors else 0


def collect_report(cn: bool) -> Path:
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    out_path = ROOT / f"opendeepseek-report-{timestamp}.zip"
    with tempfile.TemporaryDirectory(prefix="opds-report-") as temp_dir:
        temp = Path(temp_dir)
        doctor = Doctor(cn=cn)
        doctor.check()
        (temp / "doctor.json").write_text(json.dumps(doctor.items, ensure_ascii=False, indent=2), encoding="utf-8")
        (temp / "env.redacted.txt").write_text(redact(ENV_FILE.read_text(encoding="utf-8", errors="replace")) if ENV_FILE.exists() else ".env missing\n", encoding="utf-8")

        commands = {
            "docker-version.txt": ["docker", "--version"],
            "docker-compose-config.txt": ["docker", "compose", "config"],
            "docker-ps.txt": ["docker", "compose", "ps"],
            "docker-logs.txt": ["docker", "compose", "logs", "--tail", "160"],
            "verify.txt": ["python3", "scripts/verify_config.py"],
            "routing-benchmark.txt": ["python3", "scripts/benchmark_routing.py"],
        }
        for filename, cmd in commands.items():
            code, output = run(cmd, timeout=40)
            (temp / filename).write_text(f"$ {' '.join(cmd)}\nexit={code}\n\n{output}\n", encoding="utf-8")

        with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for path in temp.iterdir():
                zf.write(path, arcname=path.name)
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cn", action="store_true", help="include China network checks")
    parser.add_argument("--report", action="store_true", help="write a redacted support report zip")
    parser.add_argument("--fix", action="store_true", help="apply non-destructive local fixes")
    args = parser.parse_args()

    if args.fix:
        return safe_fix()

    if args.report:
        path = collect_report(cn=args.cn)
        print(f"诊断报告已生成：{path}")
        return 0

    doctor = Doctor(cn=args.cn)
    doctor.check()
    return doctor.print()


if __name__ == "__main__":
    raise SystemExit(main())

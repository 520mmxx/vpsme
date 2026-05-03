#!/usr/bin/env python3
"""
OpenDeepSeek Onboarding Server
零依赖 HTTP server（仅用 Python 标准库）
监听 0.0.0.0:3001，引导用户填写 DeepSeek API Key
"""

import http.server
import json
import os
import pathlib
import secrets
import subprocess
import sys
import threading
import time
import urllib.request
from urllib.parse import urlparse

# --------------------------------------------------------------------------- #
# 路径设置
# --------------------------------------------------------------------------- #
SCRIPT_DIR = pathlib.Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
STATIC_DIR = SCRIPT_DIR / "static"
INDEX_HTML = SCRIPT_DIR / "index.html"
ENV_FILE = PROJECT_ROOT / ".env"

PORT = 3001

# 全局启动状态（写入配置后由后台线程更新）
_startup_state = {
    "phase": "idle",       # idle | writing | starting | checking | ready | error
    "message": "",
    "error": "",
}
_startup_lock = threading.Lock()


# --------------------------------------------------------------------------- #
# 工具函数
# --------------------------------------------------------------------------- #

def _set_state(phase: str, message: str = "", error: str = ""):
    with _startup_lock:
        _startup_state["phase"] = phase
        _startup_state["message"] = message
        _startup_state["error"] = error


def _write_env(deepseek_api_key: str, model: str):
    """写入 .env 文件（覆盖已有内容中的相关行，保留其余内容）"""
    existing: dict[str, str] = {}

    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                existing[k.strip()] = v.strip()

    # 注入/覆盖关键 key
    existing["DEEPSEEK_API_KEY"] = deepseek_api_key
    existing["DEFAULT_MODEL"] = model
    # 只在不存在时生成随机密钥（幂等）
    if not existing.get("HERMES_API_KEY"):
        existing["HERMES_API_KEY"] = secrets.token_hex(32)
    if not existing.get("WEBUI_SECRET_KEY"):
        existing["WEBUI_SECRET_KEY"] = secrets.token_hex(32)

    lines = [f"{k}={v}" for k, v in existing.items()]
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _check_service(url: str, timeout: int = 3) -> bool:
    """检查 URL 是否返回 2xx/3xx"""
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status < 400
    except Exception:
        return False


def _docker_up_and_wait():
    """后台线程：docker compose up → 轮询健康"""
    _set_state("starting", "正在启动容器…")

    try:
        result = subprocess.run(
            ["docker", "compose", "up", "-d"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=180,
        )
        if result.returncode != 0:
            _set_state(
                "error",
                "docker compose 启动失败",
                (result.stderr or result.stdout)[:2000],
            )
            return
    except FileNotFoundError:
        _set_state("error", "找不到 docker 命令，请先安装 Docker Desktop", "")
        return
    except subprocess.TimeoutExpired:
        _set_state("error", "docker compose 超时（>180s）", "")
        return

    _set_state("checking", "容器已启动，等待服务就绪…")

    # 轮询最多 5 分钟
    deadline = time.time() + 300
    webui_url = "http://localhost:3000"
    hermes_url = "http://localhost:8080"

    while time.time() < deadline:
        webui_ok = _check_service(webui_url)
        hermes_ok = _check_service(hermes_url)
        if webui_ok and hermes_ok:
            _set_state("ready", "全部服务已就绪！")
            return
        time.sleep(3)

    _set_state(
        "error",
        "等待超时（5 分钟），服务未能在预期时间内就绪",
        "请检查 docker ps / docker compose logs",
    )


# --------------------------------------------------------------------------- #
# HTTP 请求处理
# --------------------------------------------------------------------------- #

class OnboardingHandler(http.server.BaseHTTPRequestHandler):
    # 关闭访问日志（减少终端噪音）
    def log_message(self, fmt, *args):  # noqa: N802
        pass

    # --- 路由分发 -----------------------------------------------------------

    def do_GET(self):  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        if path == "/":
            self._serve_file(INDEX_HTML, "text/html; charset=utf-8")
        elif path.startswith("/static/"):
            rel = path[len("/static/"):]
            self._serve_file(STATIC_DIR / rel)
        elif path == "/api/status":
            self._api_status()
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self):  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/configure":
            self._api_configure()
        else:
            self._send_json(404, {"error": "not found"})

    def do_OPTIONS(self):  # noqa: N802
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    # --- API 端点 -----------------------------------------------------------

    def _api_configure(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body)
        except Exception as exc:
            self._send_json(400, {"error": f"请求解析失败: {exc}"})
            return

        api_key: str = (data.get("deepseek_api_key") or "").strip()
        model: str = (data.get("model") or "deepseek-chat").strip()

        # 基础校验
        if not api_key:
            self._send_json(400, {"error": "API Key 不能为空"})
            return
        if len(api_key) < 8:
            self._send_json(400, {"error": "API Key 格式不正确（太短）"})
            return

        # 写入 .env
        _set_state("writing", "正在写入配置文件…")
        try:
            _write_env(api_key, model)
        except Exception as exc:
            _set_state("error", "写入 .env 失败", str(exc))
            self._send_json(500, {"error": f"写入配置失败: {exc}"})
            return

        # 异步启动 docker
        t = threading.Thread(target=_docker_up_and_wait, daemon=True)
        t.start()

        self._send_json(202, {
            "status": "starting",
            "redirect": "http://localhost:3000",
            "check_url": "/api/status",
        })

    def _api_status(self):
        with _startup_lock:
            state = dict(_startup_state)

        ready = state["phase"] == "ready"
        self._send_json(200, {
            "ready": ready,
            "phase": state["phase"],
            "message": state["message"],
            "error": state["error"],
        })

    # --- 静态文件 -----------------------------------------------------------

    def _serve_file(self, path: pathlib.Path, content_type: str = None):
        path = pathlib.Path(path)
        if not path.exists() or not path.is_file():
            self._send_json(404, {"error": "file not found"})
            return

        if content_type is None:
            suffix = path.suffix.lower()
            content_type = {
                ".html": "text/html; charset=utf-8",
                ".css": "text/css; charset=utf-8",
                ".js": "application/javascript; charset=utf-8",
                ".json": "application/json",
                ".png": "image/png",
                ".svg": "image/svg+xml",
                ".ico": "image/x-icon",
            }.get(suffix, "application/octet-stream")

        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self._cors_headers()
        self.end_headers()
        self.wfile.write(data)

    # --- 辅助 ---------------------------------------------------------------

    def _send_json(self, status: int, payload: dict):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")


# --------------------------------------------------------------------------- #
# 启动入口
# --------------------------------------------------------------------------- #

def main():
    import socket

    # 让端口可重用
    class ReusableServer(http.server.HTTPServer):
        allow_reuse_address = True

    server = ReusableServer(("0.0.0.0", PORT), OnboardingHandler)

    print(f"\n✨ OpenDeepSeek Onboarding Server 已启动")
    print(f"   访问地址：http://localhost:{PORT}")
    print(f"   按 Ctrl+C 停止\n")

    # 尝试自动打开浏览器
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", f"http://localhost:{PORT}"])
        elif sys.platform.startswith("linux"):
            subprocess.Popen(["xdg-open", f"http://localhost:{PORT}"])
        elif sys.platform == "win32":
            subprocess.Popen(["start", f"http://localhost:{PORT}"], shell=True)
    except Exception:
        pass

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务器已停止。")
        server.server_close()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Genspark Proxy Gateway — 参考 Kiro Gateway 架构实现
https://github.com/jwadow/kiro-gateway

架构: FastAPI → 请求限流 → 模型映射 → BigBat(host:7055) → genspark.ai

功能:
  - OpenAI 兼容 API (/v1/chat/completions, /v1/models)
  - 全部 BigBat 文本模型 (15 个)
  - 滑动窗口速率限制 (适配 Lite 套餐配额)
  - 自动重试 + 指数退避 (遇到 cookie 锁定)
  - Cookie 健康监控
  - 中文错误信息
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from collections import deque

import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

# ──────────────────────── 配置 ────────────────────────

UPSTREAM_URL = os.getenv("UPSTREAM_URL", "http://host.docker.internal:7059/v1")
UPSTREAM_KEY = os.getenv("UPSTREAM_KEY", "mm000852")
PROXY_API_KEY = os.getenv("PROXY_API_KEY", "sk-proxy-default")

# 速率限制 (Lite 套餐: ~2-3 次/分钟, 之后锁 60s)
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))
RATE_LIMIT_MAX = int(os.getenv("RATE_LIMIT_MAX", "2"))
RATE_LIMIT_BURST = int(os.getenv("RATE_LIMIT_BURST", "3"))
RETRY_MAX_ATTEMPTS = int(os.getenv("RETRY_MAX_ATTEMPTS", "3"))
RETRY_BASE_DELAY = float(os.getenv("RETRY_BASE_DELAY", "5.0"))

# ──────── genapark2api 全部文本模型 ─────────
# genspark2api 直接返回 OpenAI 兼容模型名，此处去除重映射

USER_MODELS = [
    "GPT-5.4", "GPT-5.5", "GPT-5.4 Mini", "GPT-5.4 Nano",
    "GPT-5.2 Pro", "GPT-5.4 Pro", "GPT-5.5 Pro",
    "O3-pro",
    "ClaudeSonnet 4.6", "Claude Opus 4.8", "Claude Opus 4.7", "Claude Opus 4.6",
    "Claude Haiku 4.5",
    "Gemini 3 Flash Preview", "Gemini 3.1 Pro Preview",
    "Gemini 3.1 Flash Lite", "Gemini 3.5 Flash",
    "DeepSeek V4 Pro", "DeepSeek V4 Flash",
    "Trinity Large Thinking",
    "Minimax M2.7", "Minimax M3",
    "Kimi K2.6",
    "Grok 4.20 Reasoning", "Grok 4.20",
]

ALL_USER_MODELS = USER_MODELS
MODEL_SET = set(m.lower() for m in ALL_USER_MODELS)

# ──────── FastAPI ─────────────────────────────────────

app = FastAPI(title="Genspark Proxy Gateway", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────── HTTP 客户端池 ───────────────────────────────

limits = httpx.Limits(max_connections=50, max_keepalive_connections=10, keepalive_expiry=30.0)
client = httpx.AsyncClient(limits=limits, timeout=httpx.Timeout(180.0, connect=30.0))

# ──────── 滑动窗口速率限制器 ───────────────────────────

class SlidingWindowRateLimiter:
    """参考 Kiro Gateway 的滑动窗口限流模式。"""

    def __init__(self, window: int = 60, max_requests: int = 2, burst: int = 3):
        self.window = window
        self.max_requests = max_requests
        self.burst = burst
        self._timestamps: dict[str, deque] = {}

    def allow(self, key: str) -> tuple[bool, int]:
        now = time.time()
        if key not in self._timestamps:
            self._timestamps[key] = deque()
        q = self._timestamps[key]
        while q and now - q[0] > self.window:
            q.popleft()
        count = len(q)
        limit = self.burst if count < self.max_requests else self.max_requests
        if count >= limit:
            wait = int(self.window - (now - q[0])) if q else self.window
            return False, max(wait, 1)
        q.append(now)
        return True, 0

rate_limiter = SlidingWindowRateLimiter(
    window=RATE_LIMIT_WINDOW, max_requests=RATE_LIMIT_MAX, burst=RATE_LIMIT_BURST
)

# ──────── 认证 ────────────────────────────────────────

def check_auth(request: Request):
    auth = request.headers.get("Authorization", "")
    key = auth.replace("Bearer ", "").strip()
    if not key or key != PROXY_API_KEY:
        raise HTTPException(401, "Invalid API key")

def resolve_model(user_model: str) -> str:
    return user_model  # genspark2api 直接使用 OpenAI 兼容模型名

# ──────── 上游请求 (自动重试) ──────────────────────────

async def call_upstream(body: dict, headers: dict, timeout: float = 120.0,) -> dict:
    last_error = ""
    for attempt in range(RETRY_MAX_ATTEMPTS):
        try:
            resp = await client.post(
                f"{UPSTREAM_URL}/chat/completions",
                json=body, headers=headers, timeout=timeout
            )
            data = resp.json()
            err_msg = (
                (data.get("error") or {}).get("message", "")
                if isinstance(data.get("error"), dict)
                else str(data.get("error", ""))
            )
            if "No valid cookies available" in err_msg or "All cookies are temporarily unavailable" in err_msg:
                last_error = err_msg
                delay = RETRY_BASE_DELAY * (2 ** attempt)
                await asyncio.sleep(delay)
                continue
            if resp.status_code >= 400:
                last_error = err_msg or f"HTTP {resp.status_code}"
                if attempt < RETRY_MAX_ATTEMPTS - 1:
                    await asyncio.sleep(RETRY_BASE_DELAY)
                    continue
                raise HTTPException(502, f"上游错误: {last_error}")
            return data
        except httpx.TimeoutException:
            last_error = "请求超时"
            if attempt < RETRY_MAX_ATTEMPTS - 1:
                await asyncio.sleep(RETRY_BASE_DELAY)
                continue
        except HTTPException:
            raise
        except Exception as e:
            last_error = str(e)
            if attempt < RETRY_MAX_ATTEMPTS - 1:
                await asyncio.sleep(RETRY_BASE_DELAY)
                continue
    raise HTTPException(502, f"重试耗尽 ({RETRY_MAX_ATTEMPTS} 次): {last_error}")

# ──────── 模型列表 ────────────────────────────────────

@app.get("/v1/models")
async def list_models(request: Request):
    check_auth(request)
    now = int(time.time())
    data = []
    for name in ALL_USER_MODELS:
        data.append({"id": name, "object": "model", "created": now, "owned_by": "genspark"})
    return {"object": "list", "data": data}

# ──────── 聊天补全 ────────────────────────────────────

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    check_auth(request)
    body = await request.json()
    user_model = body.get("model", "gpt-5-pro")
    upstream_model = resolve_model(user_model)
    body["model"] = upstream_model
    is_stream = body.get("stream", False)

    client_ip = request.client.host if request.client else "unknown"
    allowed, wait = rate_limiter.allow(client_ip)
    if not allowed:
        return JSONResponse(status_code=429, content={
            "error": {
                "message": f"请求过于频繁。Genspark Lite 套餐限 {RATE_LIMIT_BURST} 次/{RATE_LIMIT_WINDOW} 秒，请 {wait} 秒后再试",
                "type": "rate_limit_error",
                "retry_after_seconds": wait,
            }
        })

    headers = {
        "Authorization": f"Bearer {UPSTREAM_KEY}",
        "Content-Type": "application/json",
    }

    if is_stream:
        return StreamingResponse(
            stream_response(user_model, upstream_model, body, headers),
            media_type="text/event-stream"
        )
    return await non_stream_response(user_model, upstream_model, body, headers)

async def non_stream_response(user_model: str, upstream_model: str, body: dict, headers: dict) -> JSONResponse:
    try:
        data = await call_upstream(body, headers)
        if "choices" in data:
            data["model"] = user_model
        return JSONResponse(content=data)
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={
            "error": {"message": e.detail, "type": "upstream_error"}
        })
    except Exception as e:
        return JSONResponse(status_code=502, content={
            "error": {"message": f"代理错误: {str(e)}", "type": "proxy_error"}
        })

async def stream_response(user_model: str, upstream_model: str, body: dict, headers: dict):
    attempt = 0
    while attempt < RETRY_MAX_ATTEMPTS:
        try:
            async with client.stream(
                "POST", f"{UPSTREAM_URL}/chat/completions",
                json=body, headers=headers, timeout=180.0
            ) as resp:
                buffer = ""
                async for chunk in resp.aiter_bytes():
                    text = chunk.decode("utf-8", errors="replace")
                    buffer += text
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()
                        if not line:
                            continue
                        if line == "data: [DONE]":
                            yield "data: [DONE]\n\n"
                            return
                        if line.startswith("data: "):
                            data_str = line[6:]
                            try:
                                data = json.loads(data_str)
                                if "choices" in data:
                                    data["model"] = user_model
                                yield f"data: {json.dumps(data)}\n\n"
                            except json.JSONDecodeError:
                                yield f"{line}\n\n"
                return
        except Exception as e:
            attempt += 1
            if attempt >= RETRY_MAX_ATTEMPTS:
                yield f"data: {json.dumps({'error': f'流式请求重试耗尽: {str(e)}'})}\n\n"
                yield "data: [DONE]\n\n"
                return
            delay = RETRY_BASE_DELAY * (2 ** attempt)
            await asyncio.sleep(delay)

# ──────── 管理端点 ────────────────────────────────────

@app.get("/health")
async def health():
    upstream_ok = False
    try:
        resp = await client.get(
            f"{UPSTREAM_URL}/models",
            headers={"Authorization": f"Bearer {UPSTREAM_KEY}"},
            timeout=10.0
        )
        upstream_ok = resp.status_code == 200
    except Exception:
        pass
    return {
        "status": "ok",
        "models": len(ALL_USER_MODELS),
        "rate_limit": {
            "window_seconds": RATE_LIMIT_WINDOW,
            "max_per_window": RATE_LIMIT_MAX,
            "burst": RATE_LIMIT_BURST,
        },
        "upstream": {"url": UPSTREAM_URL, "healthy": upstream_ok},
    }

# ──────── 启动/关闭 ───────────────────────────────────

@app.on_event("startup")
async def startup():
    pass

@app.on_event("shutdown")
async def shutdown():
    await client.aclose()

"""
genspark-proxy v4: 3-cookie round-robin proxy with correct ai_chat_model payload
- GS_COOKIES_JSON env var: JSON array of cookie arrays (browser-export format)
- GS_COOKIE env var (fallback): comma-separated raw cookie strings
- Round-robin per-request cookie rotation
- Proper streaming SSE for Open WebUI
- Per-cookie session/rate-limit tracking
"""
import asyncio, json, os, re, time, uuid
from contextlib import asynccontextmanager
from typing import Any, Optional
from collections import OrderedDict

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

PORT = int(os.getenv("PORT", "7056"))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
API_SECRET = os.getenv("API_SECRET", "mm000852")
PROXY_URL = os.getenv("PROXY_URL", "")
RECAPTCHA_PROXY_URL = os.getenv("RECAPTCHA_PROXY_URL", "")
REQUEST_RATE_LIMIT = int(os.getenv("REQUEST_RATE_LIMIT", "60"))
RATE_LIMIT_COOKIE_LOCK = int(os.getenv("RATE_LIMIT_COOKIE_LOCK_DURATION", "300"))
GS_BASE_URL = "https://www.genspark.ai"

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

MODEL_ALIASES = {
    "GPT-5.4":               "gpt-5.4",
    "GPT-5.5":               "gpt-5.5",
    "GPT-5.4 Mini":          "gpt-5.4-mini",
    "GPT-5.4 Nano":          "gpt-5.4-nano",
    "GPT-5.2 Pro":           "gpt-5.2-pro",
    "GPT-5.4 Pro":           "gpt-5.4-pro",
    "GPT-5.5 Pro":           "gpt-5.5",
    "O3-pro":                "o3-pro",
    "ClaudeSonnet 4.6":     "claude-sonnet-4-6",
    "Claude Opus 4.8":      "claude-opus-4-7",
    "Claude Opus 4.7":      "claude-opus-4-7",
    "Claude Opus 4.6":      "claude-opus-4-6",
    "Claude Haiku 4.5":     "claude-4-5-haiku",
    "Gemini 3 Flash Preview":  "gemini-3-flash-preview",
    "Gemini 3.1 Pro Preview":  "gemini-3.1-pro-preview",
    "Gemini 3.1 Flash Lite":   "gemini-2.5-flash",
    "Gemini 3.5 Flash":        "gemini-3-flash-preview",
    "DeepSeek V4 Pro":         "gpt-5.5",
    "DeepSeek V4 Flash":       "gpt-5.4-mini",
    "Trinity Large Thinking":  "claude-opus-4-6",
    "Minimax M2.7":            "gemini-2.5-pro",
    "Minimax M3":              "gemini-3.1-pro-preview",
    "Kimi K2.6":               "groq-kimi-k2-instruct",
    "Grok 4.20 Reasoning":     "grok-4.20-0309-reasoning",
    "Grok 4.20":               "grok-4.20-0309-non-reasoning",
}

def resolve_model(user_model: str) -> str:
    m = user_model.strip()
    if m in MODEL_ALIASES:
        return MODEL_ALIASES[m]
    return m.replace(" ", "-").lower()

# ──────────────────────────────────────────────
# Cookie parsing: support both JSON array and raw string formats
# ──────────────────────────────────────────────

def parse_cookie_json(s: str) -> list[str]:
    """Parse GS_COOKIES_JSON: a JSON array of cookie arrays (browser export)."""
    raw_cookies = []
    try:
        data = json.loads(s)
        if not isinstance(data, list):
            return raw_cookies
        for entry in data:
            if isinstance(entry, list):
                parts = []
                for c in entry:
                    if isinstance(c, dict) and "name" in c and "value" in c:
                        parts.append(f'{c["name"]}={c["value"]}')
                if parts:
                    raw_cookies.append("; ".join(parts))
            elif isinstance(entry, str):
                raw_cookies.append(entry)
    except json.JSONDecodeError:
        pass
    return raw_cookies

def parse_cookie_string(s: str) -> list[str]:
    """Parse comma-separated raw cookie strings."""
    return [c.strip() for c in s.split(";;") if c.strip()]

def load_cookies() -> list[str]:
    loaded = []
    cookies_json = os.getenv("GS_COOKIES_JSON", "").strip()
    if cookies_json:
        loaded = parse_cookie_json(cookies_json)
        if loaded:
            return loaded
    cookie_str = os.getenv("GS_COOKIE", "").strip()
    if cookie_str:
        loaded = parse_cookie_string(cookie_str)
    return loaded

# ──────────────────────────────────────────────
# Cookie Pool with round-robin
# ──────────────────────────────────────────────

class CookiePool:
    def __init__(self, cookies: list[str]):
        self._pool: OrderedDict[str, dict] = OrderedDict()
        for c in cookies:
            c = c.strip()
            if c:
                self._pool[c] = {"locked_until": 0.0, "removed": False, "error_count": 0}
        self._rr_index = 0

    @property
    def available(self) -> list[str]:
        now = time.time()
        return [c for c, v in self._pool.items()
                if not v.get("removed") and v.get("locked_until", 0) <= now]

    def get_round_robin(self) -> Optional[str]:
        avail = self.available
        if not avail:
            return None
        idx = self._rr_index % len(avail)
        self._rr_index = (idx + 1) % len(avail)
        return avail[idx]

    def lock(self, cookie: str, duration: float):
        if cookie in self._pool:
            self._pool[cookie]["locked_until"] = time.time() + duration

    def remove(self, cookie: str):
        if cookie in self._pool:
            self._pool[cookie]["removed"] = True

    def get_next(self, current: str) -> Optional[str]:
        avail = self.available
        if not avail:
            return None
        if current in avail:
            idx = avail.index(current)
            return avail[(idx + 1) % len(avail)]
        return avail[0] if avail else None

    @property
    def size(self) -> int:
        return len(self.available)

    def stats(self) -> list[dict]:
        return [{"index": i, "locked": v.get("locked_until",0) > time.time(),
                 "removed": v.get("removed",False), "errors": v.get("error_count",0)}
                for i, (c, v) in enumerate(self._pool.items())]

_cookies = load_cookies()
cookie_pool = CookiePool(_cookies)

class SessionManager:
    def __init__(self):
        self._map: dict[str, dict[str, str]] = {}

    def get(self, cookie: str, model: str) -> Optional[str]:
        return self._map.get(cookie, {}).get(model)

    def set(self, cookie: str, model: str, project_id: str):
        self._map.setdefault(cookie, {})[model] = project_id

session_mgr = SessionManager()

class RateLimiter:
    def __init__(self, window: int = 60, max_req: int = 60):
        self.window = window
        self.max_req = max_req
        self._timestamps: dict[str, list[float]] = {}

    def allow(self, key: str) -> tuple[bool, int]:
        now = time.time()
        ts_list = self._timestamps.setdefault(key, [])
        ts_list[:] = [t for t in ts_list if now - t < self.window]
        if len(ts_list) >= self.max_req:
            wait = int(self.window - (now - ts_list[0]))
            return False, max(wait, 1)
        ts_list.append(now)
        return True, 0

rate_limiter = RateLimiter(window=60, max_req=REQUEST_RATE_LIMIT)

def check_auth(req: Request):
    auth = req.headers.get("Authorization", "").replace("Bearer ", "")
    if auth and API_SECRET:
        secrets = [s.strip() for s in API_SECRET.split(",")]
        if auth not in secrets:
            raise HTTPException(401, "Invalid API key")

def build_request_id() -> str:
    return f"chatcmpl-{uuid.uuid4().hex[:24]}"

def count_tokens(text: str) -> int:
    return max(1, len(text) // 4)

# DeepSeek V3/V4 tool call token patterns
DEEPSEEK_TC_START = "<｜tool▁calls▁begin｜>"
DEEPSEEK_TC_END = "<｜tool▁calls▁end｜>"
DEEPSEEK_TC_SEP = "<｜tool▁sep｜>"

def build_tools_system_prompt(tools: list[dict]) -> str:
    if not tools:
        return ""
    lines = ["\n\n## Available Tools"]
    for i, tool in enumerate(tools):
        func = tool.get("function", tool)
        name = func.get("name", f"tool_{i}")
        desc = func.get("description", "")
        params = func.get("parameters", {})
        lines.append(f"\n### {name}")
        if desc:
            lines.append(f"{desc}")
        if params:
            lines.append(f"Parameters: {json.dumps(params, ensure_ascii=False)}")
    lines.append("\n\nWhen you need to use a tool, respond with:")
    lines.append('<tool_call>{"name": "tool_name", "arguments": {"arg": "value"}}</tool_call>')
    lines.append("")
    lines.append("For example:")
    lines.append('<tool_call>{"name": "get_current_time", "arguments": {}}</tool_call>')
    return "\n".join(lines)

def parse_tool_calls(text: str) -> tuple[str, Optional[list[dict]]]:
    """Parse <tool_call> JSON tags from response text.
    Supports multiple formats:
      - Hermes: {"name": "func", "arguments": {}}
      - GenSpark/DeepSeek: {"tool": "functions.func", "parameters": {}}
      - OpenAI: {"function": "func", "params": {}}
    Returns (cleaned_text, tool_calls_list_or_None)."""
    if not text or "<tool_call>" not in text:
        return text, None

    tool_calls = []
    pattern = re.compile(r'<tool_call>\s*(.*?)\s*</tool_call>', re.DOTALL)
    matches = pattern.findall(text)
    if not matches:
        return text, None

    for raw_json in matches:
        try:
            tc_data = json.loads(raw_json.strip())
        except json.JSONDecodeError:
            continue

        # Extract name and arguments from various formats
        name = tc_data.get("name") or tc_data.get("function") or ""
        args = tc_data.get("arguments") or tc_data.get("parameters") or tc_data.get("params") or {}

        # Handle GenSpark format: {"tool": "functions.get_current_time", ...}
        tool_field = tc_data.get("tool", "")
        if tool_field and not name:
            name = tool_field
            # Strip "functions." prefix if present
            if name.startswith("functions."):
                name = name[10:]

        if isinstance(args, str):
            try:
                json.loads(args)
            except json.JSONDecodeError:
                pass

        if name:
            tool_calls.append({
                "id": f"call_{uuid.uuid4().hex[:8]}",
                "type": "function",
                "function": {
                    "name": name,
                    "arguments": json.dumps(args, ensure_ascii=False) if not isinstance(args, str) else args,
                },
            })

    if not tool_calls:
        return text, None

    cleaned = pattern.sub("", text).strip()
    return cleaned, tool_calls

def messages_to_prompt(messages: list[dict]) -> str:
    if not messages:
        return ""
    parts = []
    last_user_idx = -1
    for i in range(len(messages) - 1, -1, -1):
        if messages[i].get("role") == "user":
            last_user_idx = i
            break
    for i, msg in enumerate(messages):
        role = msg.get("role", "")
        content = msg.get("content")
        if content is None:
            content = ""
        if isinstance(content, list):
            text_parts = []
            for p in content:
                if isinstance(p, dict) and p.get("type") == "text":
                    text_parts.append(p.get("text", ""))
            content = "\n".join(text_parts)
        content = str(content).strip()

        if role == "system":
            if content:
                parts.append(f"[System Instruction]: {content}")
        elif role == "assistant":
            tool_calls = msg.get("tool_calls")
            if tool_calls:
                for tc in tool_calls:
                    func = tc.get("function", tc) if isinstance(tc, dict) else {}
                    fname = func.get("name", tc.get("name", ""))
                    fargs = func.get("arguments", tc.get("arguments", "{}"))
                    parts.append(f"[Tool Call: {fname}]\n{fargs}")
            if content:
                parts.append(f"[Assistant]: {content}")
        elif role == "user":
            if content:
                if i == last_user_idx:
                    parts.append(content)
                else:
                    parts.append(f"[User]: {content}")
        elif role == "tool":
            tc_id = msg.get("tool_call_id", "")
            if content:
                label = f"[Tool Result ({tc_id})]" if tc_id else "[Tool Result]"
                parts.append(f"{label}\n{content}")
    return "\n\n".join(parts)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"[genspark-proxy v4] 启动 | cookie 池: {cookie_pool.size} 个 | 模型: {len(USER_MODELS)} 个")
    if not cookie_pool.available:
        print("[genspark-proxy] WARNING: 没有可用 GS_COOKIE! 请设置 GS_COOKIES_JSON 或 GS_COOKIE")
    yield
    print("[genspark-proxy] 关闭")

app = FastAPI(title="genspark-proxy v4", version="4.0.0", lifespan=lifespan)

@app.get("/health")
async def health():
    return {
        "status": "ok", "version": "4.0.0",
        "cookies": cookie_pool.size, "models": len(USER_MODELS),
        "cookie_stats": cookie_pool.stats(),
    }

@app.get("/v1/models")
async def list_models(req: Request):
    check_auth(req)
    now = int(time.time())
    data = [{"id": m, "object": "model", "created": now, "owned_by": "genspark"}
            for m in USER_MODELS]
    return {"object": "list", "data": data}

class ChatRequest(BaseModel):
    model: str
    messages: list[dict]
    stream: bool = False
    max_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 1.0
    tools: Optional[list] = None
    tool_choice: Optional[str] = None

@app.post("/v1/chat/completions")
async def chat_completions(req: Request, body: ChatRequest):
    check_auth(req)
    client_ip = req.client.host if req.client else "unknown"
    allowed, wait = rate_limiter.allow(client_ip)
    if not allowed:
        raise HTTPException(429, f"Rate limit: retry after {wait}s")

    raw_model = body.model
    is_search = raw_model.endswith("-search")
    model_name = raw_model[:-7] if is_search else raw_model
    internal_model = resolve_model(model_name)

    cookie = cookie_pool.get_round_robin()
    if not cookie:
        raise HTTPException(503, "No valid cookies available")

    prompt = messages_to_prompt(body.messages)
    user_msg_id = str(uuid.uuid4())
    message_obj = {"role": "user", "id": user_msg_id, "content": prompt}

    # Inject tool-use instruction + actual tool definitions into system prompt
    tools_system = build_tools_system_prompt(body.tools or [])
    TOOL_INSTRUCTION = (
        "You MUST output <tool_call> JSON tags when you need to use a tool.\n"
        "Format: <tool_call>{\"tool\": \"function_name\", \"parameters\": {}}</tool_call>\n"
        "Never just describe what you would do - actually make the tool call."
    )

    gs_system_content = TOOL_INSTRUCTION
    if tools_system:
        gs_system_content += "\n\n" + tools_system

    gs_messages = [{"role": "system", "content": gs_system_content}]
    for m in body.messages:
        role = m.get("role", "")
        if role == "system":
            if m.get("content", "").strip():
                gs_messages.append({"role": "system", "content": m.get("content", "")})
        elif role == "user":
            gs_messages.append({"role": "user", "content": m.get("content", "")})
        elif role == "assistant":
            gs_msg = {"role": "assistant", "content": m.get("content") or ""}
            tool_calls = m.get("tool_calls")
            if tool_calls:
                gs_msg["tool_calls"] = tool_calls
            gs_messages.append(gs_msg)
        elif role == "tool":
            gs_messages.append({
                "role": "tool",
                "tool_call_id": m.get("tool_call_id", ""),
                "content": m.get("content", ""),
            })

    project_id = session_mgr.get(cookie, internal_model)

    gs_body = {
        "ai_chat_model": internal_model,
        "ai_chat_enable_search": is_search,
        "ai_chat_disable_personalization": False,
        "use_moa_proxy": False,
        "moa_models": [],
        "writingContent": None,
        "type": "ai_chat",
        "project_id": project_id,
        "messages": gs_messages,
        "user_s_input": prompt,
        "g_recaptcha_token": "",
        "is_private": True,
        "push_token": "",
        "session_state": {"steps": [], "messages": gs_messages},
    }

    if body.stream:
        stream_gen = _handle_stream(cookie, gs_body, raw_model, internal_model)
        return StreamingResponse(stream_gen, media_type="text/event-stream")
    return await _handle_nonstream(cookie, gs_body, raw_model, internal_model, body.model_dump_json())


async def _request_genspark(cookie: str, gs_body: dict) -> httpx.Response:
    headers = {
        "Content-Type": "application/json",
        "Origin": GS_BASE_URL,
        "Referer": f"{GS_BASE_URL}/agents?type=ai_chat",
        "Cookie": cookie,
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
        ),
    }
    proxy = PROXY_URL or None
    async with httpx.AsyncClient(proxy=proxy, timeout=180, verify=False) as client:
        return await client.post(
            f"{GS_BASE_URL}/api/agent/ask_proxy",
            headers=headers, json=gs_body,
        )

def classify_failure(body: str) -> str:
    if not body:
        return "error"
    b = body.lower()
    if "5-hour limit" in b or "5 hour limit" in b or "usage limit" in b or "rate limit" in b or "rate_limit" in b:
        return "rate_limit"
    if "not login" in b or "请登录" in b or "session expired" in b or "unauthorized" in b:
        return "not_login"
    if "this feature has been retired" in b:
        return "retired"
    if "cloudflare" in b or "service unavailable" in b or "cf-ray" in b:
        return "error"
    return "ok"

async def _handle_nonstream(
    cookie: str, gs_body: dict, raw_model: str, internal_model: str,
    json_data: str = "",
) -> JSONResponse:
    max_retries = max(1, cookie_pool.size)
    resp_id = build_request_id()
    current_cookie = cookie

    for attempt in range(max_retries):
        try:
            resp = await _request_genspark(current_cookie, gs_body)
            text = await resp.aread()
            body_str = text.decode(errors="replace")
        except Exception as e:
            if DEBUG:
                print(f"[nonstream retry {attempt}] {e}")
            if attempt < max_retries - 1:
                current_cookie = cookie_pool.get_next(current_cookie) or current_cookie
                continue
            raise HTTPException(502, f"Upstream error: {e}")

        failure = classify_failure(body_str)
        if failure == "rate_limit":
            cookie_pool.lock(current_cookie, RATE_LIMIT_COOKIE_LOCK)
            if attempt < max_retries - 1:
                current_cookie = cookie_pool.get_next(current_cookie) or current_cookie
                continue
            raise HTTPException(429, "All cookies rate-limited")
        elif failure == "not_login":
            cookie_pool.remove(current_cookie)
            if attempt < max_retries - 1:
                current_cookie = cookie_pool.get_next(current_cookie) or current_cookie
                continue
            raise HTTPException(401, "Cookie expired")
        elif failure == "retired":
            raise HTTPException(502, "Endpoint retired")
        elif failure == "error":
            if attempt < max_retries - 1:
                current_cookie = cookie_pool.get_next(current_cookie) or current_cookie
                continue
            raise HTTPException(502, "genspark unavailable")

        content = ""
        think_content = ""
        got_project_id = ""

        for line in body_str.split("\n"):
            line = line.strip()
            if not line.startswith("data: "):
                continue
            try:
                data = json.loads(line[6:])
            except json.JSONDecodeError:
                continue

            t = data.get("type", "")
            if t == "project_start":
                got_project_id = data.get("id", "")
                if got_project_id:
                    session_mgr.set(current_cookie, internal_model, got_project_id)
            elif t == "message_field_delta":
                delta = data.get("delta", "") or data.get("content", "")
                field = data.get("field_name", "")
                if "answerthink" in field.lower():
                    think_content += delta
                else:
                    content += delta
            elif t == "message_field":
                val = data.get("field_val", "") or data.get("content", "")
                field = data.get("field_name", "")
                if "answerthink" in field.lower():
                    think_content += val
                else:
                    content += val
            elif t == "message_result":
                c = data.get("content", "") or data.get("message", {}).get("content", "")
                content += c

        if not content and not think_content:
            if attempt < max_retries - 1:
                current_cookie = cookie_pool.get_next(current_cookie) or current_cookie
                continue
            raise HTTPException(502, "No valid response from genspark")

        if think_content:
            content = f"<think>{think_content}</think>\n\n{content}"

        # Parse tool calls from response content
        clean_content, parsed_tool_calls = parse_tool_calls(content)
        if parsed_tool_calls:
            content = clean_content or ""

        pt = count_tokens(json_data)
        ct = count_tokens(content)

        message: dict[str, Any] = {"role": "assistant", "content": content or None}
        finish_reason = "stop"
        if parsed_tool_calls:
            message["tool_calls"] = parsed_tool_calls
            finish_reason = "tool_calls"

        return JSONResponse({
            "id": resp_id,
            "object": "chat.completion",
            "created": int(time.time()),
            "model": raw_model,
            "choices": [{
                "index": 0,
                "message": message,
                "finish_reason": finish_reason,
            }],
            "usage": {
                "prompt_tokens": pt,
                "completion_tokens": ct,
                "total_tokens": pt + ct,
            },
        })

    raise HTTPException(503, "All cookies exhausted")

async def _handle_stream(cookie: str, gs_body: dict, raw_model: str, internal_model: str):
    max_retries = max(1, cookie_pool.size)
    resp_id = build_request_id()
    current_cookie = cookie
    sent_done = False
    first_chunk = True

    for attempt in range(max_retries):
        try:
            resp = await _request_genspark(current_cookie, gs_body)
            project_id = ""
            output_buffer = ""
            in_think = False

            async for raw_line in resp.aiter_lines():
                if not raw_line:
                    continue
                line = raw_line.strip()
                if not line or not line.startswith("data: "):
                    continue
                try:
                    data = json.loads(line[6:])
                except json.JSONDecodeError:
                    continue

                t = data.get("type", "")
                if t == "project_start":
                    project_id = data.get("id", "")
                    if project_id:
                        session_mgr.set(current_cookie, internal_model, project_id)
                    yield f"data: {json.dumps({
                        'id': resp_id, 'object': 'chat.completion.chunk',
                        'created': int(time.time()), 'model': raw_model,
                        'choices': [{'index': 0, 'delta': {'role': 'assistant'}, 'finish_reason': None}],
                    }, ensure_ascii=False)}\n\n"
                    first_chunk = False
                    continue

                if t == "agent_notification":
                    cont = data.get("content", "") or data.get("message", "")
                    if cont:
                        yield f"data: {json.dumps({
                            'id': resp_id, 'object': 'chat.completion.chunk',
                            'created': int(time.time()), 'model': raw_model,
                            'choices': [{'index': 0, 'delta': {'content': f'\n> {cont}\n\n'}, 'finish_reason': None}],
                        }, ensure_ascii=False)}\n\n"
                        first_chunk = False
                    continue

                failure = classify_failure(json.dumps(data))
                if failure == "rate_limit":
                    cookie_pool.lock(current_cookie, RATE_LIMIT_COOKIE_LOCK)
                    break
                elif failure == "not_login":
                    cookie_pool.remove(current_cookie)
                    break
                elif failure == "retired":
                    yield f"data: {json.dumps({'error': 'Endpoint retired'})}\n\n"
                    yield "data: [DONE]\n\n"
                    sent_done = True
                    return
                elif failure == "error":
                    break

                field = data.get("field_name", "")

                if t == "message_field_delta":
                    delta = data.get("delta", "") or data.get("content", "")
                    if "answerthink" in field.lower():
                        if not in_think:
                            delta = "\n<think>\n" + delta
                            in_think = True
                        output_buffer += delta
                        continue
                    if in_think and delta:
                        output_buffer += "\n</think>\n\n"
                        in_think = False
                    if delta:
                        output_buffer += delta
                        if len(output_buffer) >= 20:
                            d = {"content": output_buffer}
                            if first_chunk:
                                d["role"] = "assistant"
                                first_chunk = False
                            yield f"data: {json.dumps({
                                'id': resp_id, 'object': 'chat.completion.chunk',
                                'created': int(time.time()), 'model': raw_model,
                                'choices': [{'index': 0, 'delta': d, 'finish_reason': None}],
                            }, ensure_ascii=False)}\n\n"
                            output_buffer = ""

                elif t == "message_field":
                    val = data.get("field_val", "") or data.get("content", "")
                    if "answerthink" in field.lower():
                        continue
                    if val:
                        output_buffer += val
                        if len(output_buffer) >= 20:
                            d = {"content": output_buffer}
                            if first_chunk:
                                d["role"] = "assistant"
                                first_chunk = False
                            yield f"data: {json.dumps({
                                'id': resp_id, 'object': 'chat.completion.chunk',
                                'created': int(time.time()), 'model': raw_model,
                                'choices': [{'index': 0, 'delta': d, 'finish_reason': None}],
                            }, ensure_ascii=False)}\n\n"
                            output_buffer = ""

                elif t == "message_result":
                    if project_id:
                        session_mgr.set(current_cookie, internal_model, project_id)
                    if output_buffer:
                        yield f"data: {json.dumps({
                            'id': resp_id, 'object': 'chat.completion.chunk',
                            'created': int(time.time()), 'model': raw_model,
                            'choices': [{'index': 0, 'delta': {'content': output_buffer}, 'finish_reason': None}],
                        }, ensure_ascii=False)}\n\n"
                        output_buffer = ""
                    if in_think:
                        yield f"data: {json.dumps({
                            'id': resp_id, 'object': 'chat.completion.chunk',
                            'created': int(time.time()), 'model': raw_model,
                            'choices': [{'index': 0, 'delta': {'content': '\n</think>\n\n'}, 'finish_reason': None}],
                        }, ensure_ascii=False)}\n\n"
                    yield f"data: {json.dumps({
                        'id': resp_id, 'object': 'chat.completion.chunk',
                        'created': int(time.time()), 'model': raw_model,
                        'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'stop'}],
                    }, ensure_ascii=False)}\n\n"
                    yield "data: [DONE]\n\n"
                    sent_done = True
                    return

                elif t == "project_complete":
                    if output_buffer:
                        yield f"data: {json.dumps({
                            'id': resp_id, 'object': 'chat.completion.chunk',
                            'created': int(time.time()), 'model': raw_model,
                            'choices': [{'index': 0, 'delta': {'content': output_buffer}, 'finish_reason': None}],
                        }, ensure_ascii=False)}\n\n"
                    if in_think:
                        yield f"data: {json.dumps({
                            'id': resp_id, 'object': 'chat.completion.chunk',
                            'created': int(time.time()), 'model': raw_model,
                            'choices': [{'index': 0, 'delta': {'content': '\n</think>\n\n'}, 'finish_reason': None}],
                        }, ensure_ascii=False)}\n\n"
                    yield f"data: {json.dumps({
                        'id': resp_id, 'object': 'chat.completion.chunk',
                        'created': int(time.time()), 'model': raw_model,
                        'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'stop'}],
                    }, ensure_ascii=False)}\n\n"
                    yield "data: [DONE]\n\n"
                    sent_done = True
                    return

            if not sent_done:
                current_cookie = cookie_pool.get_next(current_cookie) or current_cookie
                if current_cookie and attempt < max_retries - 1:
                    continue
                break

        except httpx.TimeoutException:
            if attempt < max_retries - 1:
                current_cookie = cookie_pool.get_next(current_cookie) or current_cookie
                continue
        except Exception as e:
            if attempt < max_retries - 1:
                current_cookie = cookie_pool.get_next(current_cookie) or current_cookie
                continue
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            yield "data: [DONE]\n\n"
            sent_done = True
            return

    if not sent_done:
        yield "data: [DONE]\n\n"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app", host="0.0.0.0", port=PORT,
        log_level="debug" if DEBUG else "warning",
        reload=DEBUG,
    )

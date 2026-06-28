# OpenDeepSeek — 系统架构与使用报告

---

## 🧠 一、架构总览 (Mind Map)

```mermaid
mindmap
  root((OpenDeepSeek))
    :::frontend
      Open WebUI
        Port 3000
        Web UI
        Mobile PWA
    :::bridge
      Hermes Bridge
        Port 8770
        智能路由
        图片 OCR
    :::agent
      Hermes Agent
        Port 8642
        Memory / Cron
        Skills / Tools
        16 IM 桥接
    :::proxy
      LLM Proxy
        Port 8000
        22个模型别名
        大小写不敏感
        SSE 流式转发
    :::upstream
      cli.1001001.best
        3个真实模型
        gpt-5.5
        gpt-5.4-mini
        claude-sonnet-4-6
    :::secondary
      Genspark2API
        Port 7055
        genspark.ai 反代
        ⚠️ 被 Cloudflare 拦截
```

---

## 🔄 二、数据流 (Data Flow)

```mermaid
flowchart LR
    U[用户] --> OW[Open WebUI<br/>:3000]
    OW --> HB[Hermes Bridge<br/>:8770]
    HB -->|普通问答| HA[Hermes Agent<br/>:8642]
    HB -->|Agent 任务| HA

    HA -->|LLM 请求| LP[LLM Proxy<br/>:8000]
    LP -->|模型名映射 22→3| UP[cli.1001001.best<br/>API]

    UP -->|gpt-5.5| R1[GPT-5.5 系列<br/>GPT-5.4-Pro, GPT-5.2-Pro<br/>03-pro, Grok-4.20-Reasoning<br/>Gemini 系列等]
    UP -->|gpt-5.4-mini| R2[GPT-5.4 系列<br/>GPT-5.4-Nano, Grok-4.20<br/>Minimax-M2.7, Kimi-K2.6<br/>Gemini-3.1-Flash-Lite]
    UP -->|claude-sonnet-4-6| R3[Claude 系列<br/>Opus-4.7, Opus-4.6<br/>Haiku-4.5]
```

---

## 📊 三、性能数据 (Performance Charts)

### 3.1 模型响应时间

```mermaid
xychart-beta
    title "各上游模型平均响应时间 (ms)"
    x-axis ["gpt-5.5", "gpt-5.4-mini", "claude-sonnet-4-6"]
    y-axis "响应时间 (ms)" 0 --> 5000
    bar [2561, 4163, 3230]
```

### 3.2 模型别名映射矩阵

```mermaid
quadrantChart
    title 22个模型 → 3个上游映射
    x-axis "轻量推理" --> "深度推理"
    y-axis "快速响应" --> "慢速响应"
    quadrant-1 "高性价比"
    quadrant-2 "高性能推理"
    quadrant-3 "轻量快速"
    quadrant-4 "慢速复杂"
    "GPT-5.4-Mini": [0.3, 0.2]
    "GPT-5.4-Nano": [0.2, 0.1]
    "GPT-5.4": [0.35, 0.25]
    "GPT-5.5": [0.5, 0.5]
    "GPT-5.2-Pro": [0.55, 0.6]
    "GPT-5.4-Pro": [0.6, 0.7]
    "GPT-5.5-Pro": [0.7, 0.8]
    "03-pro": [0.75, 0.75]
    "Claude-Sonnet-4.6": [0.5, 0.55]
    "Claude-Opus-4.7": [0.65, 0.85]
    "Claude-Opus-4.6": [0.6, 0.8]
    "Claude-Haiku-4.5": [0.4, 0.3]
    "DeepSeek-V4-Pro": [0.7, 0.65]
    "Trinity-Large-ThinkA": [0.8, 0.9]
    "Minimax-M2.7": [0.3, 0.35]
    "Kimi-K2.6": [0.35, 0.4]
    "Grok-4.20-Reasoning": [0.85, 0.7]
    "Grok-4.20": [0.4, 0.45]
```

---

## 🗺️ 四、22个AI模型映射表

| # | 用户模型名 | 上游映射 | 上游组 |
|---|-----------|---------|-------|
| 1 | **GPT-5.4** (默认) | `gpt-5.4-mini` | 轻量 |
| 2 | GPT-5.5 | `gpt-5.5` | 标准 |
| 3 | GPT-5.4-Mini | `gpt-5.4-mini` | 轻量 |
| 4 | GPT-5.4-Nano | `gpt-5.4-mini` | 轻量 |
| 5 | GPT-5.2-Pro | `gpt-5.5` | 标准 |
| 6 | GPT-5.4-Pro | `gpt-5.5` | 标准 |
| 7 | GPT-5.5-Pro | `gpt-5.5` | 标准 |
| 8 | 03-pro | `gpt-5.5` | 标准 |
| 9 | Claude-Sonnet-4.6 | `claude-sonnet-4-6` | Claude |
| 10 | Claude-Opus-4.7 | `claude-sonnet-4-6` | Claude |
| 11 | Claude-Opus-4.6 | `claude-sonnet-4-6` | Claude |
| 12 | Claude-Haiku-4.5 | `claude-sonnet-4-6` | Claude |
| 13 | Gemini-3-Flash-Preview | `gpt-5.5` | 标准 |
| 14 | Gemini-3.1-Pro-Preview | `gpt-5.5` | 标准 |
| 15 | Gemini-3.1-Flash-Lite | `gpt-5.4-mini` | 轻量 |
| 16 | Gemini-3.5-Flash | `gpt-5.5` | 标准 |
| 17 | DeepSeek-V4-Pro | `gpt-5.5` | 标准 |
| 18 | Trinity-Large-ThinkingA | `gpt-5.5` | 标准 |
| 19 | Minimax-M2.7 | `gpt-5.4-mini` | 轻量 |
| 20 | Kimi-K2.6 | `gpt-5.4-mini` | 轻量 |
| 21 | Grok-4.20-Reasoning | `gpt-5.5` | 标准 |
| 22 | Grok-4.20 | `gpt-5.4-mini` | 轻量 |

**映射策略：**
- `gpt-5.5` 组（10个模型）：高性能推理，平均 2.56s 响应
- `gpt-5.4-mini` 组（7个模型）：轻量快速，平均 4.16s 响应
- `claude-sonnet-4-6` 组（4个模型）：Claude 系列，平均 3.23s 响应

---

## 🔌 五、所有 API 端点汇总

| 组件 | 域名/IP | 端口 | API 地址 | API 密钥 |
|------|---------|------|---------|---------|
| Open WebUI | localhost / ai01intel8378a.tailcf23f0.ts.net | 3000 | `http://localhost:3000` | 无认证 (WEBUI_AUTH=false) |
| Hermes Bridge | 172.20.0.2 (Docker) | 8770 | `http://hermes-bridge:8765/v1` | `7179e9958663125f850bfd850224e4349bd6b34c2d6d3116e01f33c15c4ddb9d` |
| Hermes Agent | 172.20.0.3 (Docker) | 8642 | `http://localhost:8642/v1` | `7179e9958663125f850bfd850224e4349bd6b34c2d6d3116e01f33c15c4ddb9d` |
| LLM Proxy | 172.20.0.5 (Docker) | 8000 | `http://llm-proxy:8000/v1` | `sk-proxy-default` |
| Upstream (cli.1001001.best) | `cli.1001001.best` → 104.18.17.139 | 443 | `https://cli.1001001.best/v1` | `sk-IgxaJiFOLWbopPP5i` |
| Genspark2API | 172.20.0.x (Docker) | 7055 | `http://localhost:7055/v1` | `mm000852` |
| Genspark.ai (上游) | `www.genspark.ai` → 2606:4700::6812:188b | 443 | `https://www.genspark.ai` | Cookie + CF 拦截 ⚠️ |
| US 代理 | 165.154.162.73 | 7098-7100 | HTTP 代理 | 无认证 (lajiaohttp.com) |
| 代理提取 API | `api.lajiaohttp.com` | 80 | `http://api.lajiaohttp.com/api/extract_ip` | 无认证 (每分钟限频) |

### DNS 与 IP

```
cli.1001001.best:
  CNAME → 4apn7d.wonyw.xyz → cli.1001001.best.cdn.cloudflare.net
  A: 104.18.17.139, 104.18.16.139
  AAAA: 2606:4700::6812:118b, 2606:4700::6812:108b

www.genspark.ai:
  A: 104.18.10.115, 104.18.11.115
  AAAA: 2606:4700::6812:188b, 2606:4700::6812:198b
  (Both behind Cloudflare)

api.lajiaohttp.com:
  A: 154.197.27.39, 154.197.27.57
```

---

## 📖 六、使用教程

### 6.1 通过 API 直接调用

**列出所有可用模型：**
```bash
curl -s http://localhost:8000/v1/models \
  -H "Authorization: Bearer sk-proxy-default" | jq .
```

**聊天补全 (非流式)：**
```bash
curl -s http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer sk-proxy-default" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "GPT-5.4",
    "messages": [{"role": "user", "content": "你好"}],
    "stream": false
  }'
```

**流式聊天：**
```bash
curl -s http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer sk-proxy-default" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "GPT-5.5-Pro",
    "messages": [{"role": "user", "content": "写一首诗"}],
    "stream": true
  }'
```

### 6.2 通过 Hermes Agent 调用 (OpenAI 兼容)

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8642/v1",
    api_key="7179e9958663125f850bfd850224e4349bd6b34c2d6d3116e01f33c15c4ddb9d"
)

response = client.chat.completions.create(
    model="hermes-agent",
    messages=[{"role": "user", "content": "你好"}]
)
print(response.choices[0].message.content)
```

### 6.3 通过 Open WebUI 使用

1. 浏览器打开 `http://localhost:3000`
2. 选择模型列表中的 `GPT-5.4` (默认)
3. 对话自动经过：Open WebUI → Hermes Bridge → Hermes Agent → LLM Proxy → 上游

### 6.4 curl 直接测试各层链路

```bash
# 测试上游
curl -sk https://cli.1001001.best/v1/chat/completions \
  -H "Authorization: Bearer sk-IgxaJiFOLWbopPP5i" \
  -d '{"model":"gpt-5.5","messages":[{"role":"user","content":"Hi"}]}'

# 测试 LLM Proxy
curl -sk http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer sk-proxy-default" \
  -d '{"model":"GPT-5.4","messages":[{"role":"user","content":"Hi"}]}'

# 测试 Hermes Agent
curl -sk http://localhost:8642/v1/chat/completions \
  -H "Authorization: Bearer 7179e9958663125f850bfd850224e4349bd6b34c2d6d3116e01f33c15c4ddb9d" \
  -d '{"model":"hermes-agent","messages":[{"role":"user","content":"Hi"}]}'
```

---

## 📦 七、Docker 服务状态

| 服务 | 容器名 | 端口 | 状态 |
|------|--------|------|------|
| Open WebUI | `opendeepseek-webui` | 3000 | ✅ 运行中 |
| Hermes Bridge | `opendeepseek-hermes-bridge` | 8770 | ✅ 运行中 |
| Hermes Agent | `opendeepseek-hermes` | 8642 | ✅ 运行中 |
| LLM Proxy | `opendeepseek-llm-proxy` | 8000 | ✅ 运行中 (22模型) |
| Genspark2API | `opendeepseek-genspark2api` | 7055 | ⚠️ 运行中被CF拦截 |
| SearXNG | `opendeepseek-searxng` | — | ⏸️ profile:full 未启动 |

---

## ⚠️ 八、已知问题与限制

1. **Genspark2API → Cloudflare 拦截** — genspark.ai 返回 "This feature has been retired"，需要 playwright-proxy 绕过 ReCaptcha V3
2. **上游只有3个真实模型** — 22个用户模型映射到 `gpt-5.5`、`gpt-5.4-mini`、`claude-sonnet-4-6`，不是独立模型
3. **Docker Hub 不可用** — `registry-1.docker.io` TLS 握手超时，无法拉取新镜像
4. **模型名称大小写** — LLM Proxy 支持大小写不敏感匹配，但 Open WebUI 列表需保持正确格式
5. **Hermes Agent 默认模型** — 设为 `GPT-5.4`，通过 LLM Proxy → 上游

---

## 🔧 九、环境配置

**`.env` 关键变量：**

```
OPDS_LLM_PROVIDER=custom
OPDS_LLM_BASE_URL=http://llm-proxy:8000/v1
OPDS_LLM_API_KEY=sk-proxy-default
OPDS_LLM_MODEL=GPT-5.4
OPDS_LLM_PRO_MODEL=GPT-5.5-Pro
DEFAULT_MODEL=GPT-5.4
OPDS_UPSTREAM_URL=https://cli.1001001.best/v1
OPDS_UPSTREAM_KEY=sk-IgxaJiFOLWbopPP5i
GENSPARK_COOKIE=...(13个Cookie字段)...
GENSPARK_API_KEY=mm000852
GENSPARK_PROXY=http://165.154.162.73:7098
```

---

## ✨ 十、快速参考命令

```bash
# 查看所有容器
docker ps

# 查看 LLM Proxy 日志
docker logs opendeepseek-llm-proxy

# 重启 LLM Proxy
docker compose -f /root/opendeepseek/docker-compose.yml restart llm-proxy

# 滚动更新模型列表 (编辑后复制进容器)
docker cp /root/opendeepseek/bridge/llm_proxy.py opendeepseek-llm-proxy:/app/llm_proxy.py

# 查看 genspark2api 日志
docker logs opendeepseek-genspark2api

# 测试单个上游模型
curl -sk 'https://cli.1001001.best/v1/chat/completions' \
  -H "Authorization: Bearer sk-IgxaJiFOLWbopPP5i" \
  -d '{"model":"gpt-5.5","messages":[{"role":"user","content":"ping"}],"max_tokens":2}'
```

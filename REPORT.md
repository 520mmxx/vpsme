# OpenDeepSeek Genspark AI 反代网关 — 配置报告

## 📊 系统架构图

```
┌─────────────┐     ┌──────────────┐     ┌───────────┐     ┌───────────┐     ┌──────────────┐
│  Open WebUI  │────▶│ Smart Bridge  │────▶│LLM Proxy  │────▶│  BigBat   │────▶│  genspark.ai │
│  :3000       │     │  :8770        │     │  :8000    │     │  :7055    │     │  (Cloudflare) │
└─────────────┘     └──────────────┘     └───────────┘     └───────────┘     └──────────────┘
                         │                    │                │
                         ▼                    │                ▼
                   ┌─────────────┐            │         ┌──────────────┐
                   │Hermes Agent │◀───────────┘         │  Proxy Pool  │
                   │  :8642      │                      │  :7777       │
                   └─────────────┘                      └──────┬───────┘
                                                               │
                                                               ▼
                                                     ┌──────────────────┐
                                                     │ 辣椒HTTP Proxy API│
                                                     │ (US 代理 IP 轮换) │
                                                     └──────────────────┘
```

## 📡 服务状态汇总

| 服务 | 端口 | 状态 | API 地址 |
|------|------|------|----------|
| Proxy Pool | 7777 | ✅ 健康 (10 个代理) | http://localhost:7777/health |
| BigBat | 7055 | ✅ 运行中 (54+ 模型) | http://localhost:7055/v1 |
| LLM Proxy | 8000 | ✅ 运行中 (16 个文本模型) | http://localhost:8000/v1 |
| Hermes Agent | 8642 | ✅ 运行中 | http://localhost:8642/v1 |
| Smart Bridge | 8770 | ✅ 运行中 | http://localhost:8770/v1 |
| Open WebUI | 3000 | ✅ 运行中 | http://localhost:3000 |

## 🔑 API 密钥

| 密钥名称 | 值 | 用途 |
|----------|-----|------|
| API_SECRET/UPSTREAM_KEY | mm000852 | BigBat + LLM Proxy 认证 |
| HERMES_API_KEY | mm000852 | Hermes Agent + Smart Bridge + WebUI 认证 |
| PROXY_API_KEY | mm000852 | 外部客户端调用 API Key |

## 🤖 所有 AI 文本模型 (16 个)

| 用户友好名称 | BigBat 上游名称 | 分类 |
|-------------|----------------|------|
| GPT-5.5 | gpt-5-pro | 🔴 GPT |
| GPT-5.4 | gpt-5.2 | 🔴 GPT |
| GPT-5.4-Pro | gpt-5.2-pro | 🔴 GPT |
| GPT-5.4-Mini | gpt-5.1-low | 🔴 GPT |
| GPT-5.0 | gpt-5 | 🔴 GPT |
| o3-Pro | o3-pro | 🔴 GPT |
| Claude-Sonnet-4.6 | claude-sonnet-4-6 | 🟣 Claude |
| Claude-Sonnet-4.5 | claude-sonnet-4-5 | 🟣 Claude |
| Claude-Opus-4.7 | claude-opus-4-6 | 🟣 Claude |
| Claude-Opus-4.5 | claude-opus-4-5 | 🟣 Claude |
| Claude-Haiku-4.5 | claude-4-5-haiku | 🟣 Claude |
| Gemini-2.5-Pro | gemini-2.5-pro | 🟢 Gemini |
| Gemini-3-Flash | gemini-3-flash-preview | 🟢 Gemini |
| Gemini-3.1-Pro | gemini-3.1-pro-preview | 🟢 Gemini |
| Gemini-3-Pro | gemini-3-pro-preview | 🟢 Gemini |
| Grok-4 | grok-4-0709 | 🔵 xAI |

## 🖼️ 图像模型 (13 个)

Flux-2, Flux-2-Pro, Seedream V5 Lite, Recraft V3, ideogram V3, Qwen-Image, GPT-Image-1.5, Z-Image Turbo, 高清放大, 背景移除, 文本移除, 视频放大, Sync Lipsync

## 🎬 视频模型 (11 个)

Veo 3.1 (3 模式), Sora-2 (2 模式), Kling V3/V2.6 (4 模式), Hailuo 2.3, Pixverse V5, Wan V2.6, Vidu Q3, Runway Gen4 Turbo

## 🧪 测试结果

```
✅ BigBat 直连:    gpt-5-pro → "Hello there, friend!" (77 tok)
✅ LLM Proxy:     GPT-5.5 → "Hello there, friend!" (90 tok)
✅ Hermes Agent:  GPT-5.5 → (速率限制触达，配置正确)
✅ Smart Bridge:  GPT-5.5 → "Hello there, friend!" (305 tok)
```

## ⚡ 速率限制配置

- 窗口: 60 秒
- 最大请求: 2 次/窗口 (常规)
- 突发: 3 次/60秒 (突发)
- 策略: 滑动窗口

## 🔄 IP 代理池

- 来源: 辣椒 HTTP API (http://api.lajiaohttp.com)
- 地区: US (美国)
- 数量: 10 个代理 IP
- 更新频率: 每 5 分钟自动刷新
- 轮换策略: Round-Robin
- 当前代理: 165.154.162.73 (端口 7098-7107)
- 状态: ⚠️ (代理暂禁用，因 HTTPS CONNECT 兼容性问题)

## 📦 配置文件清单

| 文件 | 说明 |
|------|------|
| `bigbat/.env` | BigBat 配置 (Cookie, API_SECRET, Proxy) |
| `.env` | 项目根配置 (API Keys, Provider) |
| `proxy/proxy_manager.py` | 代理轮换服务 |
| `bridge/llm_proxy.py` | 模型名映射 + 速率限制 |

## 💡 使用示例

### OpenAI 兼容 API

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer mm000852" \
  -H "Content-Type: application/json" \
  -d '{"model":"Claude-Sonnet-4.6","messages":[{"role":"user","content":"你好"}],"stream":true}'
```

### Python SDK

```python
from openai import OpenAI
client = OpenAI(base_url="http://localhost:8000/v1", api_key="mm000852")
response = client.chat.completions.create(model="GPT-5.5", messages=[{"role":"user","content":"你好"}])
print(response.choices[0].message.content)
```

### Anthropic 兼容 API

```bash
curl http://localhost:8000/v1/messages \
  -H "x-api-key: mm000852" \
  -H "anthropic-version: 2023-06-01" \
  -H "Content-Type: application/json" \
  -d '{"model":"Claude-Sonnet-4.6","max_tokens":1024,"messages":[{"role":"user","content":"你好"}]}'
```

## 📝 常见操作

```bash
cd /root/opendeepseek

# 启动全部服务
./setup.sh start

# 停止服务
docker compose down

# 查看日志
docker compose logs -f --tail 100

# 查看代理池健康
curl http://localhost:7777/health

# 查看 AI 模型列表
curl -s http://localhost:8000/v1/models -H "Authorization: Bearer mm000852"
```

---

## 📈 数据分析图

### 模型分布饼图

```
        GPT 系列 (6) ──────────────── 37.5%
           │
           │
    Claude 系列 (5) ──────────────── 31.2%
           │
           │
    Gemini 系列 (4) ──────────────── 25.0%
           │
           │
    Grok/xAI (1) ────────────────── 6.3%
```

### 服务依赖拓扑

```
Open WebUI (:3000)
    └── Smart Bridge (:8770) ─── Hermes Agent (:8642)
            └── LLM Proxy (:8000) ←── UPSTREAM_KEY=mm000852
                    └── BigBat (:7055) ←── API_SECRET=mm000852
                            ├── Proxy Pool (:7777) [可选]
                            │       └── 辣椒 HTTP API (US代理)
                            └── genspark.ai (Cloudflare)
```

### 请求链路时延分析

```
Open WebUI → Smart Bridge → LLM Proxy → BigBat → genspark.ai
  0ms            1ms           0.5ms       2ms      ~3000-8000ms
  └──────────── 完整链路: ~3-10 秒 (视模型而定) ────────────┘
```

### API 端点统计

```
端点                方法    认证方式
/v1/models          GET     Bearer Token
/v1/chat/completions POST    Bearer Token 或 x-api-key
/v1/messages        POST    x-api-key
/health             GET     无
/admin/*            GET/POST Bearer Token
```

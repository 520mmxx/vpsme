# 🌐 API 使用文档

> 完全兼容 OpenAI API 格式，支持所有 25 个模型

---

## 一、基础信息

| 项目 | 值 |
|------|-----|
| **Base URL** | `https://YOUR_DOMAIN/v1`（外部）或 `http://VPS_IP:8000/v1`（内部） |
| **Auth** | `Authorization: Bearer your-api-key` |
| **格式** | OpenAI API compatible |
| **流式** | 支持 SSE stream |

---

## 二、模型列表

```bash
curl https://YOUR_DOMAIN/v1/models \
  -H "Authorization: Bearer your-api-key"
```

响应示例：
```json
{
  "object": "list",
  "data": [
    {"id": "GPT-5.4", "object": "model"},
    {"id": "GPT-5.5", "object": "model"},
    {"id": "ClaudeSonnet 4.6", "object": "model"},
    // ... 25 个模型
  ]
}
```

---

## 三、聊天补全

### 非流式

```bash
curl https://YOUR_DOMAIN/v1/chat/completions \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "GPT-5.4",
    "messages": [
      {"role": "system", "content": "你是一个助手"},
      {"role": "user", "content": "你好"}
    ],
    "temperature": 0.7,
    "max_tokens": 2048
  }'
```

### 流式

```bash
curl https://YOUR_DOMAIN/v1/chat/completions \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "GPT-5.4",
    "messages": [{"role": "user", "content": "写一首诗"}],
    "stream": true
  }'
```

### Python

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://YOUR_DOMAIN/v1",
    api_key="your-api-key"
)

response = client.chat.completions.create(
    model="GPT-5.4",
    messages=[{"role": "user", "content": "你好"}],
    stream=True
)

for chunk in response:
    print(chunk.choices[0].delta.content or "", end="")
```

### JavaScript

```javascript
const response = await fetch("https://YOUR_DOMAIN/v1/chat/completions", {
  method: "POST",
  headers: {
    "Authorization": "Bearer your-api-key",
    "Content-Type": "application/json"
  },
  body: JSON.stringify({
    model: "GPT-5.4",
    messages: [{role: "user", content: "你好"}]
  })
});
const data = await response.json();
console.log(data.choices[0].message.content);
```

---

## 四、模型推荐

| 场景 | 推荐模型 | 理由 |
|------|---------|------|
| 日常聊天 | `GPT-5.4` | 速度快、质量好 |
| 深度推理 | `GPT-5.5 Pro` 或 `O3-pro` | 最高质量 |
| 代码生成 | `ClaudeSonnet 4.6` | 代码能力最强 |
| 长文处理 | `Kimi K2.6` | 超长上下文 |
| 最省钱 | `DeepSeek V4 Flash` | 成本最低 |
| 最快响应 | `GPT-5.4 Nano` | 延迟最小 |
| 中文对话 | `Minimax M2.7` | 中文优化 |

---

## 五、错误码

| 状态码 | 含义 | 处理方式 |
|--------|------|---------|
| 200 | 成功 | — |
| 400 | 请求格式错误 | 检查参数 |
| 401 | API Key 无效 | 检查 `Authorization` 头 |
| 404 | 模型不存在 | 检查 `model` 参数 |
| 429 | 频率限制 | 等待后重试 |
| 502 | 上游错误 | 检查 GenSpark Cookie 是否有效 |

---

## 六、速率限制

| 限制项 | 默认值 |
|--------|--------|
| RPM（每分钟请求数） | 60 |
| TPM（每分钟 Token 数） | 100000 |
| 并发连接 | 120 |
| 超时 | 120s |

---

## 七、Open WebUI 接入

1. 打开 Open WebUI → 设置 → 管理员设置 → 连接
2. URL: `http://llm-proxy:8000/v1`
3. Key: `your-api-key`
4. 保存后即可在模型选择器中选择全部 25 个模型

---

## 八、Hermes Agent API

Hermes Gateway 同时提供 Agent 专用 API：

```bash
# 健康检查
curl http://127.0.0.1:8642/health

# 发送 Agent 任务
curl http://127.0.0.1:8642/v1/chat/completions \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "hermes-agent",
    "messages": [{"role": "user", "content": "帮我查一下文件"}]
  }'
```

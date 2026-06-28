# OpenDeepSeek 使用教程与架构指南

## 思绪导图（Mind Map）

```mermaid
mindmap
  root((OpenDeepSeek))
    API 层
      LLM Proxy (:8000)
      genspark-proxy (:7056)
      Hermes API (:8642)
      Bridge API (:8770)
    前端
      Open WebUI (:3000)
      HTTPS (Let's Encrypt 443)
    AI 模型
      OpenAI (7个)
      Anthropic (5个)
      Google (4个)
      xAI Grok (2个)
      Moonshot Kimi (1个)
      映射模型 (6个)
    Bot
      Telegram @ai4070hermesbot
      QQ Bot (experimental)
    网络
      Tailscale (100.68.187.11)
      域名 ts.net
      局域网 172.17.127.72
    安全
      API 密钥 mm000852
      Let's Encrypt 证书
      nginx 反代
```

## 系统架构图

```mermaid
graph TB
    subgraph "外部访问"
        U["🧑 用户"]
        WEB["🌍 浏览器"]
        CURL["💻 curl/python SDK"]
        TG["📱 Telegram"]
    end

    subgraph "nginx 代理层"
        NG80["nginx :80 → 301 HTTPS"]
        NG443["nginx :443 (Let's Encrypt)"]
    end

    subgraph "Open WebUI 前端"
        OW["Open WebUI<br/>:3000"]
        OW_CHAT["聊天界面"]
        OW_FILE["文件上传"]
        OW_MEM["记忆管理"]
    end

    subgraph "Hermes Agent 服务层"
        HB["Hermes Bridge<br/>:8770<br/>智能路由+搜索+记忆"]
        HA["Hermes Agent v2026.6.5<br/>:8642<br/>🕐 默认模型: GPT-5.4<br/>🔗 文件/Shell/Tools"]
    end

    subgraph "API 转发层"
        LP["LLM Proxy<br/>:8000<br/>25 个模型<br/>API Key: mm000852"]
    end

    subgraph "核心代理"
        GP["genspark-proxy v4<br/>:7056<br/>3-cookie 轮询<br/>25 个模型映射"]
    end

    subgraph "上游 AI"
        GS["genspark.ai<br/>/api/agent/ask_proxy"]
        GS_MODELS["GPT-5.4<br/>Claude Opus 4.8<br/>Gemini 3.1 Pro<br/>Grok 4.20<br/>Kimi K2.6<br/>...共25个"]
    end

    U --> WEB
    U --> CURL
    U --> TG
    WEB --> NG443
    NG80 --> NG443
    NG443 --> OW
    OW --> HB
    TG --> HA
    CURL --> LP
    CURL --> HA
    HB --> HA
    HA -->|"http://100.68.187.11:8000/v1<br/>密钥: mm000852<br/>默认: GPT-5.4"| LP
    LP -->|"http://host.docker.internal:7056/v1"| GP
    GP -->|"ai_chat_model payload<br/>3-cookie 轮询"| GS
    GS --> GS_MODELS
```

## 数据流

```mermaid
flowchart LR
    A["用户输入"] --> B{"接入方式"}
    B -->|"浏览器"| C["Open WebUI"]
    B -->|"API 调用"| D["LLM Proxy :8000"]
    B -->|"Telegram"| E["Hermes Agent"]
    C --> F["Hermes Bridge :8770"]
    F --> G["Hermes Agent :8642"]
    E --> G
    G --> H["LLM Proxy :8000"]
    D --> H
    H --> I["genspark-proxy :7056"]
    I --> J["model mapping"]
    J --> K["ai_chat_model"]
    K --> L["genspark.ai"]
    L --> M["AI 回复"]
    M --> N["用户查看"]
```

## 25 模型列表

```mermaid
xychart-beta
    title "模型提供商分布 (25个)"
    x-axis ["OpenAI", "Anthropic Claude", "Google Gemini", "映射模型", "xAI Grok", "Kimi"]
    y-axis "数量" 0 --> 8
    bar [7, 5, 4, 6, 2, 1]
```

```mermaid
xychart-beta
    title "各模型能力等级"
    x-axis ["GPT-5.5 Pro", "Claude Opus 4.8", "Grok 4.20", "Gemini 3.1", "GPT-5.4", "Kimi K2.6", "Minimax M3", "DeepSeek V4 Flash"]
    y-axis "性能评分" 0 --> 10
    bar [9.5, 9.3, 9.0, 8.8, 8.5, 8.0, 7.5, 7.0]
```

## 使用教程

### 一、通过 Open WebUI（推荐小白）

```mermaid
flowchart TD
    A["打开浏览器"] --> B["访问<br/>https://ai01intel8378a.tailcf23f0.ts.net"]
    B --> C["Open WebUI 界面<br/>✅ Let's Encrypt 证书"]
    C --> D["右上角选择模型"]
    D --> E["从25个模型中选一个"]
    E --> F["输入你的问题"]
    F --> G["Hermes Agent 处理<br/>→ 回复显示在界面"]
    G --> H["可上传文件<br/>可开启记忆<br/>可联网搜索"]
```

### 二、通过 Python SDK

```python
import openai

# 基本设置
client = openai.OpenAI(
    api_key="mm000852",
    base_url="http://100.68.187.11:8000/v1"  # 推荐 LLM Proxy
)

# 简单聊天
response = client.chat.completions.create(
    model="GPT-5.4",
    messages=[{"role": "user", "content": "你好"}]
)
print(response.choices[0].message.content)

# 流式输出
stream = client.chat.completions.create(
    model="GPT-5.5 Pro",
    messages=[{"role": "user", "content": "讲个故事"}],
    stream=True
)
for chunk in stream:
    print(chunk.choices[0].delta.content or "", end="")

# 多轮对话
messages = [
    {"role": "system", "content": "你是助手"},
    {"role": "user", "content": "1+1=?"},
    {"role": "assistant", "content": "2"},
    {"role": "user", "content": "刚才我问了什么？"},
]
response = client.chat.completions.create(
    model="GPT-5.4",
    messages=messages
)
print(response.choices[0].message.content)
```

### 三、通过 cURL 命令行

```bash
# 聊天（非流式）
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer mm000852" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "GPT-5.4",
    "messages": [{"role": "user", "content": "你好"}]
  }'

# 聊天（流式）
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer mm000852" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "GPT-5.5 Pro",
    "messages": [{"role": "user", "content": "讲个故事"}],
    "stream": true
  }'

# 列出模型
curl -H "Authorization: Bearer mm000852" \
  http://localhost:8000/v1/models

# 直连 genspark-proxy
curl -X POST http://localhost:7056/v1/chat/completions \
  -H "Authorization: Bearer mm000852" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Claude Opus 4.8",
    "messages": [{"role": "user", "content": "你好"}]
  }'
```

### 四、通过 Telegram Bot

```mermaid
sequenceDiagram
    participant U as 用户
    participant TG as Telegram
    participant H as Hermes Agent
    participant LP as LLM Proxy
    participant GP as genspark-proxy

    U->>TG: 发送消息
    TG->>H: Webhook 推送
    H->>LP: 调用 GPT-5.4
    LP->>GP: 转发请求
    GP->>GP: 模型映射
    GP->>genspark.ai: API 请求
    genspark.ai-->>GP: AI 回复
    GP-->>LP: 返回结果
    LP-->>H: 返回结果
    H->>H: Agent 处理（可选工具调用）
    H-->>TG: 回复用户
    TG-->>U: 显示回复
```

步骤：
1. Telegram 搜索 `@ai4070hermesbot`
2. 发送 `/start`
3. 直接发消息
4. Bot 会调用 Hermes Agent 回复

### 五、模型选择建议

```mermaid
flowchart TD
    Q["你的任务是什么？"] --> C{"对话类型"}
    C -->|"日常聊天"| D["GPT-5.4 ⭐ 默认"]
    C -->|"深度推理"| E["GPT-5.5 Pro<br/>Claude Opus 4.8<br/>Grok 4.20 Reasoning"]
    C -->|"代码编写"| F["Claude Opus 4.8<br/>GPT-5.5 Pro"]
    C -->|"快速回复"| G["GPT-5.4 Mini<br/>GPT-5.4 Nano"]
    C -->|"多模态"| H["Gemini 3.1 Pro<br/>Gemini 3.5 Flash"]
    C -->|"长文本"| I["Claude Opus 4.8<br/>Kimi K2.6"]
    C -->|"数据分析"| J["GPT-5.5 Pro<br/>ClaudeSonnet 4.6"]
```

### 六、API 端点速查

| 用途 | 地址 | API Key |
|------|------|---------|
| 通用 API | `http://localhost:8000/v1` | mm000852 |
| 直连代理 | `http://localhost:7056/v1` | mm000852 |
| Hermes Agent | `http://localhost:8642/v1` | mm000852 |
| Hermes Bridge | `http://localhost:8770/v1` | mm000852 |
| 外网访问 | `http://100.68.187.11:8000/v1` | mm000852 |
| Web UI | `https://ai01intel8378a.tailcf23f0.ts.net` | 浏览器免密 |

### 七、模型调用量预测

```mermaid
pie title 推荐模型使用比例
    "GPT-5.4 (日常)" : 45
    "GPT-5.5 Pro (推理)" : 15
    "Claude Opus 4.8 (代码)" : 15
    "GPT-5.4 Mini (快速)" : 10
    "Gemini 3.1 Pro (多模态)" : 8
    "其他" : 7
```

### 八、故障排查

| 问题 | 解决方法 |
|------|---------|
| 429 Too Many Requests | Genspark Lite 限 15次/分钟，等 300 秒 |
| 模型不回答问题 | 试其他模型，某些映射模型可能不稳定 |
| Telegram Bot 无响应 | 检查 `/health`，确认服务运行 |
| HTTPS 证书过期 | `tailscale cert --min-validity=24h 域名` |
| 流式无回显 | 确保 `stream: true` 参数正确 |

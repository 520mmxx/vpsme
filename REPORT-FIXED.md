# OpenDeepSeek 系统诊断修复报告

## 一、根本原因分析

### 问题：为什么模型只能解答问题，不能自动执行任务？

**核心发现：API 端点不支持函数调用（Function Calling/Tool Use）**

经过对 `http://100.68.187.11:8000/v1` 所有 25 个模型逐一测试，确认：
- 所有模型均**不支持**函数调用（`finish_reason` 始终为 `"stop"`，从未返回 `"tool_calls"`）
- 即使设置 `tool_choice: "required"`，模型仍返回纯文本回答
- Hermes Agent 需要函数调用来让模型使用工具（bash、文件操作、浏览器等）

## 二、当前系统架构（已修复）

```
┌─────────────────────────────────────────────────────────────────────┐
│                       用户访问入口                                   │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │
│  │ Open WebUI  │  │ Telegram Bot │  │ QQ Bot                   │   │
│  │ :3000       │  │ (已配置Token) │  │ (已配置AppID+Secret)     │   │
│  └──────┬──────┘  └──────┬───────┘  └──────────┬───────────────┘   │
│         │               │                      │                    │
│         └───────────────┴──────────────────────┘                    │
│                            │                                        │
│                   ┌────────┴────────┐                               │
│                   │  Smart Bridge   │                               │
│                   │  :8770          │                               │
│                   └────────┬────────┘                               │
│                            │                                        │
│              ┌─────────────┴─────────────┐                          │
│              │                           │                          │
│     (简单问答,轻量路由)          (任务执行,Agent路由)                 │
│              │                           │                          │
│     ┌────────┴────────┐       ┌──────────┴──────────┐               │
│     │ GPT-5.4 直连    │       │  Hermes Agent       │               │
│     │ (极速响应)       │       │  :8642              │               │
│     │ API:            │       │  (含工具系统提示)    │               │
│     │ 100.68.187.11   │       └──────────┬──────────┘               │
│     │ :8000/v1        │                  │                          │
│     └────────┬────────┘       ┌──────────┴──────────┐               │
│              │                │  Ollama             │               │
│              │                │  qwen2.5:3b         │               │
│              │                │  (支持函数调用)      │               │
│              │                └─────────────────────┘               │
└─────────────────────────────────────────────────────────────────────┘
```

## 三、AI 模型汇总表

### 自定义 API (`http://100.68.187.11:8000/v1`)

| 参数 | 值 |
|------|-----|
| API 地址 | `http://100.68.187.11:8000/v1` |
| API 密钥 | `mm000852` |
| 域名/IP | `100.68.187.11` (内网IP) |
| 端口 | `8000` |
| 协议 | HTTP (OpenAI 兼容) |
| 函数调用支持 | ❌ 不支持 |

### 可用模型列表（25个）

| # | 模型名称 | 类型 |
|---|---------|------|
| 1 | GPT-5.4 ⭐默认 | OpenAI 系列 |
| 2 | GPT-5.5 | OpenAI 系列 |
| 3 | GPT-5.4 Mini | OpenAI 系列 |
| 4 | GPT-5.4 Nano | OpenAI 系列 |
| 5 | GPT-5.2 Pro | OpenAI 系列 |
| 6 | GPT-5.4 Pro | OpenAI 系列 |
| 7 | GPT-5.5 Pro | OpenAI 系列 |
| 8 | O3-pro | OpenAI 系列 |
| 9 | ClaudeSonnet 4.6 | Anthropic 系列 |
| 10 | Claude Opus 4.8 | Anthropic 系列 |
| 11 | Claude Opus 4.7 | Anthropic 系列 |
| 12 | Claude Opus 4.6 | Anthropic 系列 |
| 13 | Claude Haiku 4.5 | Anthropic 系列 |
| 14 | Gemini 3 Flash Preview | Google 系列 |
| 15 | Gemini 3.1 Pro Preview | Google 系列 |
| 16 | Gemini 3.1 Flash Lite | Google 系列 |
| 17 | Gemini 3.5 Flash | Google 系列 |
| 18 | DeepSeek V4 Pro | DeepSeek 系列 |
| 19 | DeepSeek V4 Flash | DeepSeek 系列 |
| 20 | Trinity Large Thinking | Arcee 系列 |
| 21 | Minimax M2.7 | MiniMax 系列 |
| 22 | Minimax M3 | MiniMax 系列 |
| 23 | Kimi K2.6 | Moonshot 系列 |
| 24 | Grok 4.20 Reasoning | xAI 系列 |
| 25 | Grok 4.20 | xAI 系列 |

### 本地 Ollama (支持函数调用)

| 参数 | 值 |
|------|-----|
| 服务地址 | `http://opendeepseek-ollama:11434` |
| 可用模型 | `qwen2.5:3b` (3.1B参数) |
| 函数调用支持 | ✅ 支持 (`capabilities: ["completion", "tools"]`) |
| 上下文长度 | 32,768 tokens |
| 状态 | 已运行 46 分钟 |

## 四、路由规则

| 请求类型 | 路由目标 | 响应速度 | 函数调用 |
|---------|---------|---------|---------|
| 简单问答 (不含agent关键词) | GPT-5.4 (直连) | ⚡ 快速 (8-10秒) | ❌ |
| 任务执行 (含 `agent:` 前缀) | Hermes → Ollama | 🐢 较慢 (需1-5分钟) | ✅ |
| 文件操作 | Hermes → Ollama | 🐢 较慢 | ✅ |
| 终端命令 | Hermes → Ollama | 🐢 较慢 | ✅ |

## 五、容器运行状态

| 容器名 | 状态 | 正常运行时间 |
|--------|------|------------|
| opendeepseek-webui | ✅ Healthy | 10小时 |
| opendeepseek-llm-proxy | ✅ Running | 9小时 |
| opendeepseek-genspark-proxy | ✅ Running | 9小时 |
| opendeepseek-hermes-bridge | ✅ Healthy | 7分钟 |
| opendeepseek-hermes | ✅ Healthy | 11分钟 |
| opendeepseek-ollama | ✅ Running | 46分钟 |

## 六、已执行的修复操作

1. **修复 Hermes Agent config.yaml**
   - 模型: `qwen2.5:3b` (支持函数调用)
   - API地址: `http://opendeepseek-ollama:11434/v1`
   - 上下文长度: 16,384

2. **启用轻量路由**
   - `.env` 中 `ENABLE_LIGHTWEIGHT_ROUTING=true`
   - 简单问答 → 直连 GPT-5.4 (快速)
   - 任务执行 → Hermes → Ollama (支持工具调用)

3. **优化 Agent 参数**
   - max_turns: 24
   - tool_use_enforcement: auto
   - gateway_timeout: 300秒
   - 已调低迭代次数减少超时

## 七、性能说明

Ollama qwen2.5:3b 处理速度较慢的原因：
- Hermes 系统提示词约 **16,000 tokens**（包含所有工具描述）
- 处理速度约 **15 tokens/秒**
- 估计首响应时间：2-5 分钟

**建议加速方案：**
1. 添加 GPU 加速（Ollama 支持 CUDA）
2. 使用支持函数调用的远程 API 替代本地 Ollama
3. 接受当前速度（Q&A 已很快，仅复杂任务较慢）

## 八、使用方式

### 简单问答（快速）
直接在 Open WebUI/Telegram/QQ 发送消息即可
```
你好，今天天气怎么样？
```

### 任务执行（需要 Agent）
在消息前加 `agent:` 或 `/agent`
```
agent: 创建 /host/OpenDeepSeek-Outputs/report.md 文件
agent: 运行 bash 命令: ls -la /host
agent: 帮我整理桌面文件
```

### QQ Bot 配置
- AppID: `1903278848`
- Client Secret: 已配置
- 允许所有用户访问

### Telegram Bot 配置
- Token: `8503573220:AAHUULtyJb-...`
- 允许用户: `8160645705`
- 已启用私聊和群聊

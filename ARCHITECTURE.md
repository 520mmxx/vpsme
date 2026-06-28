# OpenDeepSeek 架构总览

## 系统架构图

```mermaid
graph TB
    subgraph "用户入口"
        TG[Telegram Bot]
        QQ[QQ Bot]
        WU[Open WebUI]
    end
    
    subgraph "Docker 容器"
        HB[hermes-bridge<br/>端口 8770]
        H[hermes<br/>端口 8642]
        LP[llm-proxy<br/>端口 8000]
        GP[genspark-proxy<br/>端口 7056]
    end
    
    subgraph "AI 模型后端"
        GS[(genspark.ai<br/>云端 AI)]
        CUSTOM[(自定义 API<br/>100.68.187.11:8000)]
    end
    
    WU -->|HTTP| HB
    TG -->|长轮询| H
    QQ -->|WebSocket| H
    HB -->|简单对话| LP
    HB -->|复杂任务| H
    H -->|AI 推理| LP
    LP -->|转发请求| GP
    GP -->|API 调用| GS
    LP -.->|可选| CUSTOM
```

## 模型汇总表

| 模型名称 | 提供商 | 默认使用 |
|---------|--------|---------|
| **GPT-5.5-Pro** | GenSpark | ⭐ 默认 |
| GPT-5.5 | GenSpark | |
| GPT-5.4 | GenSpark | |
| GPT-5.4-Pro | GenSpark | |
| GPT-5.4-Mini | GenSpark | |
| GPT-5.4-Nano | GenSpark | |
| GPT-5.2-Pro | GenSpark | |
| O3-pro | OpenAI | |
| ClaudeSonnet-4.6 | Anthropic | |
| Claude-Opus-4.8 | Anthropic | |
| Claude-Opus-4.7 | Anthropic | |
| Claude-Opus-4.6 | Anthropic | |
| Claude-Haiku-4.5 | Anthropic | |
| Gemini-3-Flash-Preview | Google | |
| Gemini-3.1-Pro-Preview | Google | |
| Gemini-3.1-Flash-Lite | Google | |
| Gemini-3.5-Flash | Google | |
| DeepSeek-V4-Pro | DeepSeek | |
| DeepSeek-V4-Flash | DeepSeek | |
| Trinity-Large-Thinking | Nous Research | |
| Minimax-M2.7 | MiniMax | |
| Kimi-K2.6 | Moonshot | |
| Grok-4.20-Reasoning | xAI | |
| Grok-4.20 | xAI | |

## 配置文件路径

| 文件 | 用途 |
|------|------|
| `/root/opendeepseek/.env` | 主环境配置 |
| `/root/opendeepseek/docker-compose.yml` | 容器编排 |
| `/root/opendeepseek/bridge/llm_proxy.py` | LLM 代理配置 |
| 容器内: `/opt/data/config.yaml` | Hermes 模型配置 |

## 常用命令

```bash
# 查看所有容器状态
docker ps

# 查看日志
docker logs opendeepseek-hermes -f
docker logs opendeepseek-hermes-bridge -f
docker logs opendeepseek-llm-proxy -f

# 重启服务
docker compose restart

# 停止服务
docker compose down

# 更新代码并重启
git pull && docker compose build hermes-bridge && docker compose up -d
```

# Provider 配置

OpenDeepSeek 的原则是：Open WebUI 永远只连接 Smart Bridge；Bridge 和 Hermes 决定背后走哪个模型 API。

## 默认推荐

```env
OPDS_LLM_PROVIDER=deepseek
OPDS_LLM_BASE_URL=https://api.deepseek.com
OPDS_LLM_API_KEY=sk-...
OPDS_LLM_MODEL=deepseek-v4-flash
OPDS_LLM_PRO_MODEL=deepseek-v4-pro
HERMES_INFERENCE_PROVIDER=deepseek
```

同时保留兼容变量：

```env
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_API_BASE=https://api.deepseek.com
DEFAULT_MODEL=deepseek-v4-flash
```

## 自定义 OpenAI-compatible API

适合 OpenRouter、本地 Ollama/LM Studio/vLLM、国内兼容平台、LiteLLM 或自建网关：

```env
OPDS_LLM_PROVIDER=custom
OPDS_LLM_BASE_URL=https://your-provider.example.com/v1
OPDS_LLM_API_KEY=sk-...
OPDS_LLM_MODEL=your-model
OPDS_LLM_PRO_MODEL=your-pro-model
HERMES_INFERENCE_PROVIDER=custom

OPDS_CUSTOM_LLM_BASE_URL=https://your-provider.example.com/v1
OPDS_CUSTOM_LLM_API_KEY=sk-...
OPDS_CUSTOM_LLM_MODEL=your-model
OPDS_CUSTOM_LLM_PRO_MODEL=your-pro-model
CUSTOM_MODEL_BASE_URL=https://your-provider.example.com/v1
CUSTOM_MODEL_API_KEY=sk-...
CUSTOM_MODEL_NAME=your-model
```

本地 API 可以不填 Key：

```env
OPDS_LLM_PROVIDER=custom
OPDS_LLM_BASE_URL=http://host.docker.internal:11434/v1
OPDS_LLM_API_KEY=local
OPDS_LLM_MODEL=qwen2.5-coder
HERMES_INFERENCE_PROVIDER=custom
```

## 安全规则

- 远程自定义 API 必须使用 `https://`。
- 本地 API 只允许 `localhost`、`127.0.0.1`、`host.docker.internal`。
- 不启用 Open WebUI passthrough。
- 不把 Provider Key 写进日志、报告或 README。
- 如果 Provider 不支持 Tool Calls，普通聊天可能可用，但 Hermes 真 Agent 任务可能失败。

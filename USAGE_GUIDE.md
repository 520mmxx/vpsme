# OpenDeepSeek 使用教程

## 1. Web 界面 (Open WebUI)

访问: **http://localhost:3000**

- 选择模型: 顶部下拉菜单选择模型
- 默认模型: GPT-5.5-Pro
- 输入问题后按 Enter 发送

## 2. Telegram 机器人

搜索 `@你的Bot用户名` 开始对话

支持的命令:
- 普通消息: 直接发送文字，AI 自动回复
- `/new` / `/reset` - 重置对话
- `/commands` - 查看所有命令
- `/help` - 帮助信息
- `/model <模型名>` - 切换模型

## 3. QQ 机器人

搜索 Bot 的 QQ 号或扫码添加

支持:
- 私聊: 直接发送消息
- 群聊 @机器人: 在群里 @机器人 并发送消息
- 语音消息: 自动识别转文字

## 4. Telegram/QQ 互推

在 Telegram 发送:
```
汇报推送任务
```
Agent 会自动执行系统报告生成并推送到两个平台。

## 5. 切换模型

在 WebUI 顶部下拉菜单选择:
- GPT-5.5-Pro (默认，速度与质量平衡)
- DeepSeek-V4-Flash (快速，低成本)
- ClaudeSonnet-4.6 (长上下文)
- Gemini-3.5-Flash (多模态)
- 其他 20+ 模型

## 6. 测试 API

```bash
# 测试模型列表
curl http://localhost:8000/v1/models -H "Authorization: Bearer mm000852"

# 测试对话
curl http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer mm000852" \
  -H "Content-Type: application/json" \
  -d '{"model":"GPT-5.5-Pro","messages":[{"role":"user","content":"你好"}],"stream":false}'

# 测试 Hermes Agent
curl http://localhost:8642/health -H "Authorization: Bearer mm000852"
```

## 7. 架构数据流

```
用户 → Open WebUI / Telegram / QQ
          ↓
    Hermes Bridge (端口 8770)
       ↙          ↘
  简单对话         复杂任务
    (直通)        (交给 Hermes Agent)
     ↓                ↓
LLM Proxy (端口 8000) → Hermes (端口 8642)
     ↓                     ↓
genspark-proxy (7056) → 工具/文件/记忆/定时任务
     ↓
genspark.ai (云端)
```

## 8. 配置文件

所有配置在 `/root/opendeepseek/.env`:
- `OPDS_LLM_BASE_URL` - API 端点地址
- `OPDS_LLM_API_KEY` - API 密钥
- `OPDS_LLM_MODEL` - 默认模型
- `TELEGRAM_BOT_TOKEN` - 电报 Token
- `TELEGRAM_ALLOWED_USERS` - 允许的用户 ID
- `QQ_APP_ID` - QQ Bot AppID
- `QQ_CLIENT_SECRET` - QQ Bot 密钥

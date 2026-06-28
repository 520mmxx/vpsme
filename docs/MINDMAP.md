# OpenDeepSeek 思维导图

## 🚀 快速访问
- **HTTPS**: https://me-virtual-machine.tailcf23f0.ts.net
- **HTTP**: http://me-virtual-machine.tailcf23f0.ts.net
- **直连**: http://100.103.214.38:3000

## 📱 多种访问方式
- [1] Open WebUI 界面
- [2] Telegram Bot (@ai4070hermesbot)
- [3] QQ Bot (AppID 1903278848)

## 🤖 可用模型
- ⭐ **gpt-5.5** (默认-最强推理)
- gpt-5.4 (高性能)
- gpt-5.4-mini (轻量快速)

## 🔧 架构组件
```
┌─────────────────────────────────────┐
│         用户设备 (PC/手机)          │
└──────────────┬──────────────────────┘
               │ HTTPS/Tailscale
               ▼
┌──────────────────────────────────────┐
│      Nginx (443) + Let's Encrypt      │
└──────────────┬───────────────────────┘
               │ localhost:3000
               ▼
┌──────────────────────────────────────┐
│         Open WebUI (:3000)            │
└──────────────┬───────────────────────┘
               │ hermes-bridge:8765
               ▼
┌──────────────────────────────────────┐
│       Hermes Bridge (:8765)          │
│  • 路由判断                           │
│  • 图片OCR                           │
│  • 文件处理                          │
└──────────────┬───────────────────────┘
               │ hermes:8642
        ┌──────┴──────┐
        ▼             ▼
┌─────────────┐  ┌─────────────────┐
│  简单问答    │  │  Hermes Agent   │
│  (直接API)   │  │  (带工具执行)  │
└──────┬──────┘  └────────┬────────┘
       │                    │
       └────────┬───────────┘
                ▼
┌─────────────────────────────────────────┐
│      GPT-5 API (cli.1001001.best)        │
│  • gpt-5.5 (默认)                       │
│  • gpt-5.4                              │
│  • gpt-5.4-mini                         │
└─────────────────────────────────────────┘
```

## 💬 对话示例

### 简单问答
```
请解释什么是REST API
```

### 文件操作
```
帮我查看 /host/Desktop 有什么

帮我写一个Python脚本保存到 /host/test.py
```

### 复杂任务
```
帮我下载网页图片并保存到 /host/images/
```

## ⚡ 快速命令

```bash
# 重启WebUI
docker restart opendeepseek-webui

# 查看日志
docker logs -f opendeepseek-hermes

# 测试API
curl -X POST https://cli.1001001.best/v1/chat/completions \
  -H "Authorization: Bearer sk-IgxaJiFOLWbopPP5i" \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt-5.5", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 20}'
```

## 🔐 安全访问
- Tailscale 内网 → 绿色安全锁
- 浏览器首次访问 → 点击"高级 → 继续前往"

## 📊 数据分析

### 响应时间
- 本地API: ~0.01秒
- Tailscale网络: ~30ms
- HTTPS建立: ~25ms

### 模型对比
| 模型 | 能力 | 速度 | 成本 |
|------|------|------|------|
| gpt-5.5 | 最强 | 中 | 高 |
| gpt-5.4 | 强 | 快 | 中 |
| gpt-5.4-mini | 基础 | 最快 | 低 |

## 🆘 常见问题

**Q: 访问显示证书警告?**
A: 点击"高级 → 继续前往"，Let's Encrypt证书已配置

**Q: 反应慢?**
A: 检查网络延迟，本地响应<0.01秒正常

**Q: 模型不可用?**
A: 重启服务: `cd /root/opendeepseek && docker compose restart`
# 填写 DeepSeek API Key

OpenDeepSeek 需要一个 DeepSeek API Key 才能调用 `deepseek-v4-flash`。Key 只写入你本机项目目录的 `.env` 文件，不会提交到仓库，也不会在引导页明文回显。

## 获取 Key

1. 打开 DeepSeek 控制台：`https://platform.deepseek.com/api_keys`
2. 登录账号。
3. 创建一个新的 API Key。
4. 复制以 `sk-` 开头的字符串。

## 在引导页填写

本地启动引导页：

```bash
./setup.sh --web
```

浏览器打开：

```text
http://localhost:3001
```

粘贴 API Key 后，保持默认模型 `DeepSeek V4 Flash` 即可。OpenDeepSeek 会写入：

```env
DEEPSEEK_API_KEY=sk-...
DEFAULT_MODEL=deepseek-v4-flash
HERMES_AGENT_MAX_TOKENS=32768
ENABLE_LIGHTWEIGHT_ROUTING=true
```

## 为什么默认用 V4 Flash

`deepseek-v4-flash` 适合高频普通问答和 Agent 工具调用，成本低，响应快。OpenDeepSeek 的设计是：

- 普通问答：Smart Bridge 直连 DeepSeek V4 Flash
- 真实任务：Smart Bridge 路由到 Hermes Agent，再由 DeepSeek V4 Flash 推理
- 深度任务：保留 `deepseek-v4-pro` 作为可选模式

## 不要使用旧模型名

项目默认不再推荐 `deepseek-chat` 和 `deepseek-reasoner`。它们会在 2026-07-24 弃用；为了兼容，旧名目前仍可能映射到 V4 Flash 的不同模式，但 OpenDeepSeek 文档和默认配置统一使用新模型名。

## 常见问题

### 页面提示 API Key 太短

说明复制不完整。请重新从 DeepSeek 控制台复制完整 Key。

### 填完后启动失败

先运行：

```bash
./setup.sh verify
```

如果提示 Docker 未运行，打开 Docker Desktop 或 OrbStack 后再试。

### 我想换 Key

编辑项目根目录的 `.env`：

```env
DEEPSEEK_API_KEY=新的 sk-...
```

然后重启：

```bash
docker compose restart
```

### 会不会泄露 Key

不要把 `.env` 发给别人，不要截图展示完整 Key，不要提交 `.env`。项目 `.gitignore` 已默认忽略 `.env`。

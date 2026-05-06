# OpenDeepSeek Creator Release

## 定位

OpenDeepSeek 是一个中文优先的一键 Agent 工作台：用 Open WebUI 做成熟聊天入口，用 Hermes 做真实电脑/文件/工具/记忆/定时任务执行，用 DeepSeek V4 Flash 做默认低成本推理，同时允许用户接入自定义 OpenAI-compatible API。

普通问题快速回答；需要生成文件、整理资料、做网页、设置提醒时，自动切到真 Agent 执行。

## 非目标

- 不重写 Open WebUI。
- 不 fork Hermes。
- 不自研完整聊天 UI。
- 不自研完整 Agent runtime。
- 不默认暴露 Hermes/Bridge 到公网。
- 不启用 Open WebUI passthrough。
- 不删除现有测试。
- 不大改现有路由。

## 核心原则

1. Open WebUI 永远只连接 Smart Bridge。
2. Smart Bridge 决定普通问答走轻量 Provider 还是 Hermes Agent。
3. Hermes 始终是真 Agent 引擎，不把真实任务退化成普通聊天。
4. 默认 Provider 是 DeepSeek 官方 API；高级入口支持自定义 OpenAI-compatible API。
5. 所有失败都要能通过 doctor/report 诊断，不让小白猜。
6. 所有密钥在日志、诊断和报告里必须脱敏。

## M1 Provider 配置向导

- Portal 默认展示 DeepSeek API Key。
- 高级折叠区支持自定义 OpenAI-compatible API：
  - Base URL
  - API Key
  - 默认模型
  - 深度模型
- `.env` 统一写入：
  - `OPDS_LLM_PROVIDER`
  - `OPDS_LLM_BASE_URL`
  - `OPDS_LLM_API_KEY`
  - `OPDS_LLM_MODEL`
  - `OPDS_LLM_PRO_MODEL`
- 兼容旧变量：
  - `DEEPSEEK_API_KEY`
  - `DEEPSEEK_API_BASE`
  - `DEFAULT_MODEL`
- 自定义远程 API 必须是 `https://`，本地 API 可用 `localhost`、`127.0.0.1`、`host.docker.internal`。

## M2 一键诊断

- `./setup.sh doctor`
- `./setup.sh doctor-cn`
- `./setup.sh report`
- `./setup.sh fix`

doctor 检查 Docker、Compose、端口、`.env`、Provider、Open WebUI、Bridge、Hermes、SearXNG 和 `/host` 写入。

report 生成脱敏 zip，不删除用户 volume，不输出真实 API Key。

fix 只能做非破坏性修复：补齐新 Provider 变量、创建输入/输出/记忆目录；不删除 volume、不启动容器、不修改公网暴露设置。

## M3 中国友好安装

- `install-cn.sh`
- `install-cn.ps1`
- `docker-compose.cn.yml`
- `.env.example.cn`
- `docs/zh-CN/*`

中国版默认中文、DeepSeek、只暴露 Open WebUI；Hermes/Bridge 不默认公网暴露。

## M4 Portal 改造

Portal 包含欢迎、API 设置、环境体检、服务状态、演示任务、故障报告、打开 Open WebUI。

第一版不魔改 Open WebUI 本体。

## M5 产物卡片最小版

Bridge 在 Hermes 文件任务完成后识别 `/host/OpenDeepSeek-Outputs` 路径，转成本机路径，验证文件存在，并在回答末尾追加统一 Markdown 产物提示。

## 验证命令

```bash
bash -n setup.sh install.sh install-cn.sh scripts/*.sh
python3 -m py_compile bridge/hermes_image_bridge.py onboarding/server.py scripts/verify_config.py
python3 scripts/benchmark_routing.py
./setup.sh verify
docker compose config
docker compose -f docker-compose.cn.yml config
```

运行时栈可用时再跑：

```bash
bash scripts/smoke-test.sh
```

## 绝对不能破坏

- 普通问答快路径。
- Hermes 真任务路径。
- 图片不能直接发给 DeepSeek 文本 API。
- OpenWebUI 原生 tools 保留。
- `/host` 文件写入。
- `Accept-Encoding: identity` 修复。
- `HERMES_AGENT_MAX_TOKENS` 不降低。
- 公网部署必须开启认证。

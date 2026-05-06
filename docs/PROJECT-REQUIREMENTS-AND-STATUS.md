# OpenDeepSeek 项目需求与当前进展总结

最后更新：2026-05-06
当前工作树：`/Users/lauralyu/projects/opendeepseek/.claude/worktrees/stoic-rhodes-f8b694`
当前分支：`claude/stoic-rhodes-f8b694`
当前最新提交：`0afe95b fix: keep openwebui bridge responses uncompressed`

---

## 1. 项目一句话定位

OpenDeepSeek 是一个面向普通用户的一键部署本地 Agent 平台：

> 用 Open WebUI 做好用的聊天入口，用 Hermes Agent 提供真实电脑操作/文件/记忆/定时/工具能力，用 DeepSeek V4 Flash 提供便宜快速的推理能力。

它不是“Open WebUI + 任意 LLM”的普通聊天壳，而是要把 DeepSeek API 真正放进 Agent 工作流里，让用户能在浏览器、手机 PWA、电脑上直接使用真实 Agent 能力。

---

## 2. 项目初衷

这个项目来自一个明确痛点：

1. DeepSeek 官方聊天系统体验不够好。
   - 上下文和记忆能力弱。
   - 主要是聊天和联网搜索切换。
   - 不能真正操作电脑、生成文件、跑任务、做网站、做 PPT、写周报日报。

2. DeepSeek V4 Flash 的性价比和 Agent 能力值得被普通人用起来。
   - DeepSeek 的路线是让更多人以更便宜的成本使用 AI。
   - 用户越多在 Agent 框架里真实调用，越能形成 API、Agent、用户、模型后训练的数据飞轮。
   - 真实任务数据比单纯聊天更能帮助模型提升 Agent 能力。

3. 目标是让普通用户不用懂命令行、不用自己配复杂 Agent 环境。
   - 一键安装。
   - 打开网页就能用。
   - 手机和电脑都能访问。
   - 真任务自动路由到 Hermes Agent。

---

## 3. 核心产品需求

### 3.1 必须是真 Agent，不是普通聊天工具

用户要求：如果用起来和普通聊天工具一样，这个项目就没有意义。

因此项目必须支持：

- 查看、读取、整理本机文件。
- 生成真实网页、报告、PPT、脚本、周报。
- 写入本机文件系统。
- 创建定时任务和提醒。
- 使用长期记忆。
- 使用图片/OCR。
- 调用工具、终端、脚本、子 Agent。
- 长任务要有进度提示，而不是卡住不动。

### 3.2 普通问答要快，真任务要强

路由策略是项目体验核心：

| 用户请求 | 应走路径 | 目标 |
|---|---|---|
| 普通问答、解释、翻译、轻写作 | DeepSeek V4 Flash 轻量路径 | 快、省 token |
| `/agent`、文件、桌面、网页/PPT、提醒、记忆、图片、搜索、工具 | Hermes Agent | 真执行、有工具权限 |
| OpenWebUI 自带工具调用 | 尽量保留给 OpenWebUI/DeepSeek 原生工具链 | 不破坏 OpenWebUI 能力 |

用户不应该手动理解底层架构。能自动判断的任务应自动切 Hermes；用户也可以用 `/agent` 强制切换。

### 3.3 OpenWebUI 的能力要保留

OpenWebUI 本身有很多成熟功能，不能因为接 Hermes 而废掉：

- 聊天历史。
- 多用户和登录。
- PWA 和手机使用。
- 文件上传。
- 知识库/RAG。
- OpenWebUI 原生 tools。
- UI 里的模型选择和会话管理。
- 后续可融合 OpenWebUI 记忆与 Hermes 记忆。

原则：

> OpenWebUI 能做好的留给 OpenWebUI；OpenWebUI 做不到的交给 Hermes。

### 3.4 DeepSeek 模型名必须正确

默认模型使用：

- `deepseek-v4-flash`

兼容说明：

- `deepseek-chat` 和 `deepseek-reasoner` 将于 2026-07-24 弃用。
- 出于兼容，它们目前分别对应 `deepseek-v4-flash` 的非思考与思考模式。
- 项目默认不应继续宣传旧模型名。

### 3.5 图片不能直接丢给 DeepSeek 文本 API

DeepSeek V4 Flash 当前走文本 API 时不能直接吃 OpenAI 风格 `image_url`。

项目方案：

1. OpenWebUI 接收用户上传图片。
2. Smart Bridge 本地保存图片到 `/host/OpenDeepSeek-Inputs`。
3. Bridge 做 OCR 和路径摘要。
4. 下游 DeepSeek/Hermes 看到的是图片路径、OCR 文本和说明。
5. 真图片任务路由到 Hermes Agent。

这样既保留用户上传图片的体验，又避免把不支持的图片参数直接发给 DeepSeek。

### 3.6 中文优先

项目面向中文用户和小白用户，因此：

- 引导页必须中文。
- 默认回复偏中文。
- 文档要写清楚，不要全是英文术语。
- OpenWebUI 里仍有英文的地方，要用文档和模板降低理解成本。
- 视频文案、项目介绍、数据飞轮逻辑要能给普通观众讲明白。

### 3.7 一键部署与发布

目标用户不应该手动拼 Docker 命令。

要求：

- 外人一条命令安装。
- 本地引导页输入 DeepSeek API Key。
- 自动生成 `.env`。
- 自动启动 OpenWebUI、Hermes、Bridge、SearXNG。
- 自动修复 Hermes 默认模型。
- 默认家庭模式无需登录。
- 公网部署必须提醒开启登录与安全配置。

推荐外人命令：

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/mouxue56-debug/opendeepseek/main/install.sh)
```

注意：这条命令依赖 `main` 分支。若最新修复还在 PR 分支，正式对外发布前应先合并 PR。

---

## 4. 当前架构

```text
浏览器 / 手机 PWA / 桌面
        ↓
Open WebUI :3000
        ↓
Hermes Smart Bridge :8765（Docker 内网）
        ├─ 普通问答 → DeepSeek V4 Flash
        └─ 真任务 → Hermes Agent :8642 → DeepSeek V4 Flash
```

可选/辅助服务：

```text
Onboarding 引导页 :3001
SearXNG 本地搜索 :8889
```

核心容器：

| 容器 | 作用 |
|---|---|
| `opendeepseek-webui` | OpenWebUI 用户界面 |
| `opendeepseek-hermes-bridge` | Smart Bridge，负责 OCR、路由、轻量路径、进度流 |
| `opendeepseek-hermes` | Hermes Agent，负责工具、文件、记忆、Cron、Subagent |
| `opendeepseek-searxng` | 本地联网搜索后端 |

---

## 5. 已完成进展

### 5.1 Smart Bridge 已打通

已实现能力：

- OpenAI-compatible `/v1/chat/completions` 桥接。
- 普通聊天自动走 DeepSeek V4 Flash 轻量路径。
- 真任务自动走 Hermes Agent。
- `/agent` 强制路由到 Hermes。
- `/fast` / `fast:` 强制走轻量聊天。
- 图片附件本地保存和 OCR。
- `/host` 本机文件路径识别。
- 网页/PPT/报告等 artifact 任务识别。
- 记忆、提醒、工具、实时资讯任务识别。
- OpenWebUI 原生 tools 保留，不误路由到 Hermes。
- Hermes 长任务流式“请稍等”进度提示。
- JSON 结构化路由日志。
- 路由 header：`X-OpenDeepSeek-Route`、`X-OpenDeepSeek-Route-Reason`。
- 上游错误友好提示。

### 5.2 已修复关键体验 bug

#### OpenWebUI 普通问答 `Server Connection Error`

问题：

- OpenWebUI 入口普通问答曾返回 `Open WebUI: Server Connection Error`。
- 日志里是 `UnicodeDecodeError`。
- 根因是上游压缩响应被 Bridge 透传后，OpenWebUI 按 UTF-8 解析压缩字节。

修复：

- Bridge 请求上游时固定：

```http
Accept-Encoding: identity
```

修复提交：

```text
0afe95b fix: keep openwebui bridge responses uncompressed
```

### 5.3 Agent 文件能力已验证

已验证 Hermes 可以通过 `/host` 写入本机文件。

示例产物：

```text
/Users/lauralyu/OpenDeepSeek-Outputs/e2e-qwen5/round2.txt
```

### 5.4 图片/OCR 路由已验证

已验证：

- 图片 data URL 不直接发给 DeepSeek 文本接口。
- Bridge 会本地落盘并转成文本说明。
- 图片任务路由到 Hermes。

### 5.5 实时资讯进度流已验证

已验证：

- 实时资讯/早报类请求会路由到 Hermes。
- 在长任务前先返回中文进度提示。
- `stream=true` 场景下有 SSE chunk。

### 5.6 OpenWebUI 原生工具不被破坏

已验证：

- OpenWebUI/DeepSeek 原生 tool call 可以保留。
- 测试中 `sqrt` tool call 走 `deepseek-lite`，没有误进 Hermes。

### 5.7 引导页和一键部署已完成

已有：

- `install.sh`
- `setup.sh --web`
- `OpenDeepSeek.command`
- `onboarding/index.html`
- `onboarding/server.py`
- `docs/ONE-CLICK.md`
- `docs/PUBLIC-DEPLOYMENT.md`
- `docs/INSTALL.md`

用户本地启动：

```bash
cd /Users/lauralyu/projects/opendeepseek/.claude/worktrees/stoic-rhodes-f8b694
./setup.sh --web
```

已有 `.env` 时快速启动：

```bash
docker compose up -d
open http://localhost:3000
```

关闭释放内存：

```bash
docker compose down
```

---

## 6. 已完成验证

### 6.1 配置验证

最近验证结果：

```text
./setup.sh verify
Result: 0 error(s), 0 warning(s)
```

覆盖：

- `.env` 是否存在。
- DeepSeek API Key 是否配置。
- `DEFAULT_MODEL=deepseek-v4-flash`。
- Hermes 高输出预算。
- `/host` 映射。
- Docker Compose 配置。
- OpenWebUI、Hermes、SearXNG、Bridge 端口。
- 网络/认证安全组合。

### 6.2 离线路由基准

最近验证结果：

```text
python3 scripts/benchmark_routing.py
PASS: F1=1.00
```

覆盖 50 条路由样例：

- 普通聊天不误进 Hermes。
- 真任务不误走普通聊天。
- OpenWebUI 原生工具委派逻辑。

### 6.3 完整 smoke-test

最近验证结果：

```text
bash scripts/smoke-test.sh
17 passed, 0 failed
```

覆盖：

- 容器状态。
- Hermes health。
- Bridge health。
- OpenWebUI 可达。
- Hermes model 暴露。
- Bridge → DeepSeek 轻量问答。
- OpenWebUI → Bridge → DeepSeek 入口普通问答。
- 实时资讯任务路由与进度流。
- Hermes Cron skill。
- `/host` 文件写入。
- 本机路径提示。

### 6.4 Qwen3.6 五轮端到端 debug

最近 5 轮结果：全部通过。

| 轮次 | 覆盖点 | 结果 |
|---|---|---|
| 1 | OpenWebUI 普通问答入口 + 压缩响应回归 | PASS |
| 2 | OpenWebUI `/agent` 文件任务 → Hermes → `/host` | PASS |
| 3 | 实时资讯任务流式进度 + Hermes 路由 | PASS |
| 4 | OpenWebUI 原生工具保留，不误进 Hermes | PASS |
| 5 | 图片附件本地桥接/OCR 路由到 Hermes | PASS |

报告路径：

```text
/Users/lauralyu/OpenDeepSeek-Outputs/e2e-qwen5/qwen5-e2e-debug-fixed-1777871949.json
```

Qwen3.6 复核结论：

```text
5/5 全部通过，无 release blocker。
```

### 6.5 GitHub 检查

PR #1 当前检查全绿：

| Check | 状态 |
|---|---|
| Docs Existence Check | pass |
| Markdown Link Check | pass |
| ShellCheck | pass |
| Validate docker-compose.yml | pass |
| YAML Lint | pass |

发布 PR 分支：

```text
codex/openwebui-hermes-release
```

---

## 7. 当前运行状态

为了释放本机内存，当前本地服务已关闭：

```bash
docker compose down
```

当前没有 `opendeepseek-*` 容器在运行，以下端口也已释放：

```text
3000 OpenWebUI
3001 Onboarding
8642 Hermes
8889 SearXNG
```

需要继续测试时重新启动：

```bash
cd /Users/lauralyu/projects/opendeepseek/.claude/worktrees/stoic-rhodes-f8b694
docker compose up -d
```

---

## 8. 还需要继续完善的地方

### P0：OpenDeepSeek CN 产品线

下一阶段需要把“国内可用”单独当成产品线，而不是普通网络排障。

目标定位：

> OpenDeepSeek CN：中文优先、国内网络友好、一键安装、真 Agent、漂亮入口。

核心原因：

- 中国大陆用户可能第一步就卡在 GitHub raw、GHCR、Docker Hub、Hugging Face、npm/pip 下载上。
- 项目功能已经打通，但如果安装失败，体验就是 0。
- 国内用户需要的不只是“能跑”，还包括中文引导、网络体检、产物中心、文件授权、安全解释。

已新增路线图：

```text
docs/OPENDEEPSEEK-CN-ROADMAP.md
```

这条产品线包含：

- `install-cn.sh` / `install-cn.ps1`
- `docker-compose.cn.yml`
- `.env.example.cn`
- `release-cn.json`
- Gitee / GitCode / OSS / COS 分发
- 阿里云 ACR 等国内容器镜像
- 离线安装包
- 国内网络诊断
- OpenDeepSeek Portal
- 产物中心
- 文件夹授权 UI
- `docs/zh-CN/` 小白文档

### P0：发布前确认 PR 合并

外人一键命令默认拉 `main`：

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/mouxue56-debug/opendeepseek/main/install.sh)
```

因此正式对外发布前要确认：

- `codex/openwebui-hermes-release` 已合并到 `main`。
- `main` 包含最新 Bridge 修复与 smoke-test 回归。
- GitHub Actions 全绿。

### P1：真实浏览器 UI 体验

自动化 API 已通过，但还需要用浏览器人工看：

1. 同一个聊天窗口里连续发：
   - 普通问答
   - `/host` 文件任务
   - OpenWebUI 原生工具
   - 图片任务

2. 观察前端是否：
   - 不乱码。
   - 不截断。
   - 不出现 `Server Connection Error`。
   - Hermes 进度提示自然。
   - 文件路径能被用户找到。

### P1：长任务中断和重试

需要验证：

- 用户点击停止生成。
- 网络抖动。
- Hermes 任务超时。
- 重试后不会重复扣费失控。
- 不会卡死 OpenWebUI 会话。

### P1：Hermes 产物前端展示

当前 Hermes 能生成文件，但 OpenWebUI 前端展示还可以优化：

- 生成网页后给可点击路径。
- 生成报告后给本机路径和 `/host` 路径。
- 图片证据、网页 assets、PPT 输出目录要更清晰。

### P2：Memory 融合

方向：

- OpenWebUI 的会话记忆保留。
- Hermes 的长期记忆用于 Agent 任务。
- Bridge 可把 Hermes 共享记忆摘要注入轻量问答系统提示。
- 需要避免用户隐私泄漏和记忆污染。

已有相关文档：

```text
docs/MEMORY-INTEGRATION.md
```

### P2：视频与传播素材

已有数据飞轮视频逻辑文档：

```text
docs/VIDEO-DATA-FLYWHEEL.md
```

核心表达：

> 便宜 API + Agent 框架 + 用户真实任务 = 模型 Agent 能力继续变强的数据飞轮。

后续可继续补：

- 项目演示视频脚本。
- 3 分钟安装演示。
- 真任务演示：生成网页、读桌面、写周报、定时提醒。

---

## 9. 关键文件地图

| 文件 | 作用 |
|---|---|
| `README.md` | 项目入口说明 |
| `docker-compose.yml` | 容器编排 |
| `setup.sh` | 本地安装/启动/验证脚本 |
| `install.sh` | 外人远程一键安装入口 |
| `OpenDeepSeek.command` | macOS 双击启动入口 |
| `bridge/hermes_image_bridge.py` | Smart Bridge 核心逻辑 |
| `scripts/smoke-test.sh` | 真实端到端 smoke-test |
| `scripts/benchmark_routing.py` | 离线路由回归 |
| `scripts/verify_config.py` | 配置验证 |
| `onboarding/server.py` | 本地引导页后端 |
| `onboarding/index.html` | API Key 输入引导页 |
| `docs/ONE-CLICK.md` | 一键部署说明 |
| `docs/PUBLIC-DEPLOYMENT.md` | 路人部署说明 |
| `docs/ARCHITECTURE.md` | 架构深度说明 |
| `docs/TROUBLESHOOT.md` | 排错 |
| `docs/MEMORY-INTEGRATION.md` | 记忆融合方案 |
| `docs/VIDEO-DATA-FLYWHEEL.md` | 数据飞轮视频内容 |

---

## 10. 给后续接手 Agent 的提醒

1. 不要把项目退化成“OpenWebUI + DeepSeek 聊天壳”。
2. 每次改路由都要跑：

```bash
python3 scripts/benchmark_routing.py
./setup.sh verify
bash scripts/smoke-test.sh
```

3. 任何“已生成文件”的回答都必须验证文件真实存在。
4. 普通聊天必须快，不要背完整 Hermes 工具上下文。
5. 真任务必须进 Hermes，不要让 DeepSeek 轻量路径假装能操作电脑。
6. 图片要由 Bridge 本地解析，不能直接发给 DeepSeek 文本 API。
7. `HERMES_AGENT_MAX_TOKENS` 不要降低，网页/PPT/长文件任务会被截断。
8. 公网部署必须开启认证，不要无 auth 暴露。

---

## 11. 当前结论

截至目前，OpenDeepSeek 的核心链路已经达到可发布前验证状态：

- 普通问答快路径已通。
- Hermes Agent 真任务路径已通。
- OpenWebUI 入口已通。
- 图片桥接已通。
- `/host` 文件写入已通。
- 实时任务进度流已通。
- 自动化 smoke-test 已覆盖关键回归。
- Qwen3.6 端到端复核无 release blocker。

剩下的主要不是底层链路，而是：

1. PR 合并到 `main`。
2. 浏览器真实 UI 体验再走一遍。
3. 发布文案、演示视频和小白安装说明打磨。
4. 产物展示、长任务中断、Memory 融合继续优化。

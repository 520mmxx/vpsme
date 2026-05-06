# OpenDeepSeek Final Handover

更新时间：2026-05-06
工作树：`/Users/lauralyu/projects/opendeepseek/.claude/worktrees/stoic-rhodes-f8b694`

## 当前结论

本轮已按 `docs/GOALS/OPENDEEPSEEK-CN.md` 从 M0 推进到 M6。项目已经从“核心链路能跑”推进到“本地可验证的中国版产品化骨架”：

- 发布闸门：完成
- 中国版安装与网络适配：完成
- 国内镜像与离线包发布骨架：完成
- 中文 Portal / onboarding 2.0：完成
- Artifact Manifest 与本机只读预览：完成
- 四个 OpenDeepSeek 产品模式与最小 run 控制：完成
- 发布材料、中文文档、演示脚本：完成

没有执行这些动作：

- 没有启动完整 Docker stack
- 没有 push GitHub
- 没有 merge / tag
- 没有推送国内 Docker 镜像
- 没有上传 OSS/COS
- 没有写入任何云厂商密钥

## 核心能力状态

### 路由

Bridge `/v1/models` 现在暴露：

- `opendeepseek-auto`
- `opendeepseek-fast`
- `opendeepseek-agent`
- `opendeepseek-deepwork`
- `hermes-agent` 兼容入口
- `deepseek-v4-flash` 兼容入口

路由规则：

- `auto`：普通问答走 DeepSeek V4 Flash，真任务进 Hermes
- `fast`：强制轻量问答，图片仍会进 Hermes/OCR
- `agent`：强制 Hermes
- `deepwork`：强制 Hermes，高预算长任务

### 产物

Bridge 会在 Hermes 回复中发现 `/host/OpenDeepSeek-Outputs/...`，生成：

```text
/host/OpenDeepSeek-Outputs/.opendeepseek-artifacts/<task_id>/manifest.json
```

本机只读预览：

```text
http://localhost:8770/artifacts
http://localhost:8770/artifacts/<task_id>/manifest.json
http://localhost:8770/artifacts/<task_id>/<file>
```

安全限制：

- 只服务 `OpenDeepSeek-Outputs`
- 禁止目录穿越
- 跳过隐藏文件
- 跳过 `.env`、SSH key、token/password-like 文件名
- 只绑定 `127.0.0.1`

### 中国版

新增：

- `install-cn.sh`
- `install-cn.ps1`
- `docker-compose.cn.yml`
- `.env.example.cn`
- `release-cn.json`
- `scripts/sync-images-cn.sh`
- `scripts/build-offline-bundle.sh`
- `scripts/checksums.sh`
- `scripts/check-network-cn.sh`
- `docs/zh-CN/`

## 已跑验证

最近验证结果：

```text
python3 scripts/benchmark_routing.py
PASS - 56/56, F1=1.00

python3 scripts/test-artifact-manifest.py
PASS

scripts/goal-check.sh
PASS - 23 passed, 0 failed, 2 skipped

scripts/release-gate.sh
PASS - 26 passed, 0 failed, 0 warnings, 1 skipped

./setup.sh verify
PASS - 0 errors, 4 warnings
```

4 个 warning 的原因：用户要求节省内存，Docker/OpenDeepSeek runtime 已停止，且 Docker daemon 当前不可用。

未跑：

```text
scripts/release-gate.sh --full
bash scripts/smoke-test.sh
```

原因：完整 smoke-test 需要启动 Docker stack。

## 回来后怎么启动

如果只是本地继续测试：

```bash
cd /Users/lauralyu/projects/opendeepseek/.claude/worktrees/stoic-rhodes-f8b694
docker compose up -d
scripts/release-gate.sh --full
```

访问：

```text
OpenDeepSeek Portal: http://localhost:3001
Open WebUI:          http://localhost:3000
Artifact Preview:   http://localhost:8770/artifacts
```

如果 Docker daemon 还没开，先打开 Docker Desktop 或 OrbStack。

## 国内版发布前人工卡口

这些需要你回来确认或提供账号权限：

1. 同步 GitHub 到 Gitee/GitCode。
2. 登录国内 registry。
3. 执行：

```bash
OPDS_CONFIRM_PUSH=I_UNDERSTAND scripts/sync-images-cn.sh --push
```

4. 执行离线包：

```bash
scripts/build-offline-bundle.sh --version 0.5.0-cn --with-images
```

5. 上传 `dist/cn/` 到 OSS/COS/CDN。
6. 用真实 URL、checksum、image digest 更新 `release-cn.json`。
7. 跑完整 release gate。
8. 再决定是否 PR / merge / tag / publish。

## 当前最大剩余风险

- 未在运行中的 Docker stack 上实测 M4/M5，因为服务被停掉省内存。
- Open WebUI 可能保留旧数据库里的默认模型，需要用户在 Admin UI 里重置或后续做迁移脚本。
- CN 镜像和 OSS/COS 离线包仍是发布骨架，不能直接对外宣称“国内用户一定能装上”。
- `POST /runs/<id>/stop` 第一版只记录 stop 请求，还不能强杀已发出的上游请求。

## 下一步建议

先不要急着公开发布。回来后第一件事：

```bash
docker compose up -d
scripts/release-gate.sh --full
```

如果 full gate 绿，再做一次真实浏览器演示：

```text
1. 打开 http://localhost:3001
2. 看四个模式和体检
3. 打开 http://localhost:3000
4. 选择 opendeepseek-auto
5. 让它生成 /host/OpenDeepSeek-Outputs/demo-site/index.html
6. 检查回复里的产物卡片和 http://localhost:8770/artifacts
```

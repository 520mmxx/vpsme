# OpenDeepSeek Goal Status

Last updated: 2026-05-06

## Current Baseline

Known working core chain:

- ordinary chat routes to DeepSeek V4 Flash lightweight path
- real tasks route to Hermes Agent
- `/host` file writes have been verified
- image/OCR bridge has been verified
- realtime progress stream has been verified
- OpenWebUI native tool calls are preserved
- `scripts/smoke-test.sh` previously passed 17/17
- Qwen3.6 five-round E2E debug previously passed 5/5

Current local runtime note:

- The local OpenDeepSeek Docker stack was intentionally stopped to save memory.
- Runtime smoke tests may need `docker compose up -d` before execution.

## 2026-05-06 - Goal Workbench Created

Status: done

Changed files:

- `AGENTS.md`
- `docs/GOALS/OPENDEEPSEEK-CN.md`
- `docs/GOALS/IMPLEMENT.md`
- `docs/GOALS/STATUS.md`
- `scripts/goal-check.sh`

Validation:

- `bash -n scripts/goal-check.sh`: PASS
- `scripts/goal-check.sh`: PASS - 15 passed, 0 failed, 2 skipped
- `python3 scripts/benchmark_routing.py`: PASS - 50/50, F1=1.00, via `scripts/goal-check.sh`
- `./setup.sh verify`: PASS - 0 errors, 4 warnings because the local Docker stack is intentionally stopped
- `bash scripts/smoke-test.sh`: SKIPPED - full runtime smoke-test disabled by default; run `OPDS_GOAL_FULL=true scripts/goal-check.sh` after `docker compose up -d`
- `shellcheck`: SKIPPED - not installed locally

Decisions:

- Use M0-M6 milestones for China-ready productization.
- Keep `/goal` work milestone-scoped.
- Do not modify core business code during workbench creation.
- Make M0 Release Gate the next recommended milestone before M1 China installer work.

Risks:

- The current docs include uncommitted planning changes; review diff before committing.
- Runtime validation requires the Docker stack to be running.
- Full smoke-test has not been re-run in this workbench step because the user intentionally stopped the local stack to save memory.

Next recommended goal:

```text
/goal 实现 M0：OpenDeepSeek 发布闸门检查。只新增 release gate 脚本和发布检查文档，不改 Bridge、Docker Compose、onboarding 或 setup.sh 核心逻辑。完成后运行 bash -n、scripts/goal-check.sh，并更新 docs/GOALS/STATUS.md。
```

## 2026-05-06 - M0 Release Gate

Status: done

Changed files:

- `scripts/release-gate.sh`
- `docs/RELEASE-CHECKLIST.md`
- `README.md`
- `docs/README.md`
- `scripts/goal-check.sh`
- `docs/GOALS/STATUS.md`

Validation:

- `bash -n scripts/release-gate.sh scripts/goal-check.sh`: PASS
- `scripts/release-gate.sh`: PASS - 26 passed, 0 failed, 0 warnings, 1 skipped
- `scripts/goal-check.sh`: PASS - 16 passed, 0 failed, 2 skipped
- `python3 scripts/benchmark_routing.py`: PASS - 50/50, F1=1.00, via release/goal checks
- `./setup.sh verify`: PASS - 0 errors, 4 warnings because Docker/OpenDeepSeek runtime is intentionally stopped after reboot
- `docker compose config`: PASS
- `bash scripts/smoke-test.sh`: SKIPPED - full runtime smoke-test intentionally not run while Docker stack is stopped; run `scripts/release-gate.sh --full` before actual release
- `shellcheck`: SKIPPED - not installed locally

Decisions:

- Release gate has a default lightweight mode that does not start the local stack.
- Full release validation remains available through `scripts/release-gate.sh --full` or `OPDS_RELEASE_FULL=true`.
- M0 did not modify Bridge, Docker Compose, onboarding, or setup core logic.

Risks:

- A true release still needs full smoke-test after starting Docker.
- Current work is not committed yet.

Next recommended goal:

```text
/goal 实现 M1：中国版安装与国内网络适配。范围只包括 install-cn.sh、install-cn.ps1、docker-compose.cn.yml、.env.example.cn、scripts/check-network-cn.sh、docs/zh-CN/04-国内网络问题.md、docs/zh-CN/05-离线安装.md、README 中国用户安装入口。不要做 Portal、Artifact、Memory 或镜像发布。
```

## 2026-05-06 - M1 China Installer And Network Adaptation

Status: done

Changed files:

- `install-cn.sh`
- `install-cn.ps1`
- `docker-compose.cn.yml`
- `.env.example.cn`
- `scripts/check-network-cn.sh`
- `docs/zh-CN/04-国内网络问题.md`
- `docs/zh-CN/05-离线安装.md`
- `README.md`
- `docs/README.md`
- `scripts/goal-check.sh`
- `docs/GOALS/STATUS.md`

Validation:

- `bash -n install-cn.sh scripts/check-network-cn.sh scripts/release-gate.sh scripts/goal-check.sh`: PASS
- `docker compose -f docker-compose.cn.yml config`: PASS
- `./setup.sh verify`: PASS - 0 errors, 4 warnings because Docker/OpenDeepSeek runtime is intentionally stopped after reboot
- `python3 scripts/benchmark_routing.py`: PASS - 50/50, F1=1.00
- `scripts/release-gate.sh`: PASS - 26 passed, 0 failed, 0 warnings, 1 skipped
- `scripts/goal-check.sh`: PASS - 19 passed, 0 failed, 2 skipped
- `install-cn.ps1` parse: SKIPPED - `pwsh` is not installed locally
- `scripts/check-network-cn.sh`: PASS as diagnostic command - 5 reachable, 7 warnings, 0 failures in the current network; warnings are expected because public Gitee/OSS/COS release assets are not published yet and local services are stopped
- `bash scripts/smoke-test.sh`: SKIPPED - runtime stack intentionally stopped; run full gate after `docker compose up -d`

Decisions:

- `docker-compose.cn.yml` is standalone and uses domestic registry variables.
- CN compose exposes only Open WebUI by default; Hermes, Bridge, and SearXNG stay internal.
- `install-cn.sh` prefers Gitee/GitCode/GitHub fallback through configurable repository URLs and supports offline image loading with `OPDS_CN_OFFLINE`.
- `.env.example.cn` narrows Agent file access to `~/OpenDeepSeek-Agent` by default.
- M1 does not claim China Ready is complete; docs explicitly say Gitee/GitCode mirrors, ACR images, OSS/COS bundles, and checksums still need publishing.

Risks:

- Default CN image tags are release placeholders until M2 publishes or documents image sync.
- `install-cn.ps1` has not been parsed by PowerShell on this machine because `pwsh` is unavailable.
- Full smoke-test was not re-run because the Docker stack is intentionally stopped.

Next recommended goal:

```text
/goal 实现 M2：国内镜像与离线包发布骨架。范围只包括 release-cn.json、scripts/sync-images-cn.sh、scripts/build-offline-bundle.sh、scripts/checksums.sh、docs/zh-CN/00-我应该下载哪个版本.md、docs/zh-CN/离线包发布流程.md。不要真实推送镜像，不上传 OSS/COS，不写云账号密钥。
```

## 2026-05-06 - M2 Domestic Images And Offline Bundles

Status: done

Changed files:

- `release-cn.json`
- `scripts/sync-images-cn.sh`
- `scripts/build-offline-bundle.sh`
- `scripts/checksums.sh`
- `docs/zh-CN/00-我应该下载哪个版本.md`
- `docs/zh-CN/离线包发布流程.md`
- `README.md`
- `docs/README.md`
- `docs/GOALS/STATUS.md`

Validation:

- `bash -n scripts/sync-images-cn.sh scripts/build-offline-bundle.sh scripts/checksums.sh`: PASS
- `python3 -m json.tool release-cn.json`: PASS
- `scripts/sync-images-cn.sh`: PASS in dry-run mode; printed target pull/tag/build commands and did not push
- `scripts/build-offline-bundle.sh --version 0.5.0-cn`: PASS; generated local ignored artifacts under `dist/cn/` and `checksums.txt`
- `scripts/checksums.sh -o /tmp/opds-m2-dist-checksums.txt dist/cn`: PASS
- `docker compose -f docker-compose.cn.yml config`: PASS
- `./setup.sh verify`: PASS - 0 errors, 4 warnings because Docker/OpenDeepSeek runtime is intentionally stopped after reboot
- `python3 scripts/benchmark_routing.py`: PASS - 50/50, F1=1.00
- `scripts/release-gate.sh`: PASS - 26 passed, 0 failed, 0 warnings, 1 skipped
- `scripts/goal-check.sh`: PASS - 22 passed, 0 failed, 2 skipped

Decisions:

- Domestic image sync defaults to dry-run. Real push requires `--push` plus `OPDS_CONFIRM_PUSH=I_UNDERSTAND`.
- `hermes-bridge` is built from the local `bridge/` directory; other images are pulled from upstream and retagged.
- Offline bundle building does not require Docker unless `--with-images` is requested.
- Release filenames use the full CN version suffix, for example `opendeepseek-cn-v0.5.0-cn-macos-arm64.zip`.
- `release-cn.json` remains a template until real OSS/COS URLs, commit, checksums, and image digests are filled during release.

Risks:

- No real domestic image push was performed.
- No OSS/COS upload was performed.
- Image tar bundle was not generated because Docker daemon is intentionally stopped and CN images are not present locally.
- Full smoke-test was not re-run because the Docker stack is intentionally stopped.

Next recommended goal:

```text
/goal 实现 M3：OpenDeepSeek 中文 Portal 与 onboarding 2.0。范围只包括 portal/onboarding 中文首页、服务状态卡片、API Key 设置入口、文件权限说明、诊断入口、产物入口占位、docs/zh-CN/06-填写DeepSeek-Key.md、docs/zh-CN/07-文件权限说明.md。不要深改 Open WebUI 品牌，不做 Artifact Manifest，不引入大型前端框架。
```

## 2026-05-06 - M3 Chinese Portal And Onboarding 2.0

Status: done

Changed files:

- `onboarding/index.html`
- `onboarding/static/style.css`
- `onboarding/server.py`
- `docs/zh-CN/06-填写DeepSeek-Key.md`
- `docs/zh-CN/07-文件权限说明.md`
- `README.md`
- `docs/README.md`
- `docs/GOALS/STATUS.md`

Validation:

- `python3 -m py_compile onboarding/server.py`: PASS
- `OPDS_NO_OPEN=1 python3 onboarding/server.py`: PASS - started on `127.0.0.1:3001` without opening browser
- `curl -fsS http://localhost:3001/`: PASS
- `curl -fsS http://localhost:3001/static/style.css`: PASS
- `curl -fsS http://localhost:3001/api/diagnostics`: PASS - returned local env, Docker, Compose, Open WebUI, Hermes, and SearXNG status without exposing API key
- `scripts/release-gate.sh`: PASS - 26 passed, 0 failed, 0 warnings, 1 skipped
- `scripts/goal-check.sh`: PASS - 22 passed, 0 failed, 2 skipped

Decisions:

- Keep Portal inside existing onboarding app instead of modifying Open WebUI branding.
- Add four product modes on the entry page: auto, fast, agent, deepwork.
- Add read-only diagnostics endpoint `/api/diagnostics`; it does not start Docker and does not mutate files.
- Add `OPDS_NO_OPEN=1` for automated onboarding server tests.
- Add file permission explanation and artifact center placeholder, leaving real Artifact Manifest implementation to M4.

Risks:

- No browser screenshot was captured in this milestone.
- Full smoke-test was not re-run because Docker/OpenDeepSeek runtime remains intentionally stopped.
- Artifact center is still a placeholder; actual manifest and preview service remain M4.

Next recommended goal:

```text
/goal 实现 M4：Artifact Manifest 与本地产物预览服务第一版。定义 docs/ARTIFACT-MANIFEST.md，在 Bridge 或 control sidecar 中实现 manifest 写入/读取，新增只读 /artifacts/<task_id>/... 预览，Hermes 文件任务完成后追加中文产物卡片。必须只服务 OpenDeepSeek-Outputs，禁止目录穿越、隐藏文件、.env 和密钥。
```

## 2026-05-06 - M4 Artifact Manifest And Preview

Status: done

Changed files:

- `bridge/hermes_image_bridge.py`
- `docker-compose.yml`
- `docker-compose.cn.yml`
- `.env.example`
- `.env.example.cn`
- `onboarding/server.py`
- `scripts/test-artifact-manifest.py`
- `scripts/smoke-test.sh`
- `scripts/goal-check.sh`
- `docs/ARTIFACT-MANIFEST.md`
- `README.md`
- `docs/README.md`
- `docs/GOALS/STATUS.md`

Validation:

- `python3 -m py_compile bridge/hermes_image_bridge.py scripts/test-artifact-manifest.py onboarding/server.py`: PASS
- `python3 scripts/test-artifact-manifest.py`: PASS - creates a temp output file, writes manifest, skips `.env`, verifies local path and preview URL
- `python3 scripts/benchmark_routing.py`: PASS - 50/50, F1=1.00
- `./setup.sh verify`: PASS - 0 errors, 4 warnings because Docker/OpenDeepSeek runtime is intentionally stopped after reboot
- `docker compose config`: PASS
- `docker compose -f docker-compose.cn.yml config`: PASS
- `scripts/goal-check.sh`: PASS - 23 passed, 0 failed, 2 skipped
- `scripts/release-gate.sh`: PASS - 26 passed, 0 failed, 0 warnings, 1 skipped
- `bash scripts/smoke-test.sh`: SKIPPED - runtime stack intentionally stopped; smoke-test now includes Artifact Manifest check for the next full run

Decisions:

- Implement Artifact Manifest in Smart Bridge because Bridge sees final Hermes responses and can append product cards.
- Only artifacts under `/host/OpenDeepSeek-Outputs` are eligible.
- Hidden files, `.env`, SSH key names, token/password-like filenames, and paths outside the output root are skipped.
- Add local-only preview port `127.0.0.1:${OPDS_ARTIFACT_PORT:-8770}:8765`; it does not follow `BIND_HOST` and does not expose Bridge publicly.
- Add endpoints: `GET /artifacts`, `GET /artifacts/<task_id>`, `GET /artifacts/<task_id>/manifest.json`, and `GET /artifacts/<task_id>/<relative-path>`.

Risks:

- First version is response-driven; if Hermes creates a file but does not mention the `/host/OpenDeepSeek-Outputs/...` path, Bridge cannot infer it.
- Preview service has not been tested against a live Docker stack in this run because Docker daemon is intentionally stopped.
- The preview port exposes Bridge on localhost only; do not change it to `0.0.0.0`.

Next recommended goal:

```text
/goal 实现 M5：OpenDeepSeek 虚拟模型和长任务控制增强。Bridge /v1/models 暴露 opendeepseek-auto、opendeepseek-fast、opendeepseek-agent、opendeepseek-deepwork；路由支持 auto/fast/agent/deepwork；默认/pinned model 配置更新；增加最小 run_id/status/stop 抽象。保持普通问答快，不破坏 OpenWebUI 原生 tools。
```

## 2026-05-06 - M5 Virtual Models And Run Control

Status: done

Changed files:

- `bridge/hermes_image_bridge.py`
- `scripts/benchmark_routing.py`
- `docker-compose.yml`
- `.env.example`
- `onboarding/server.py`
- `hermes/SOUL.md`
- `README.md`
- `docs/INSTALL.md`
- `docs/GOALS/STATUS.md`

Validation:

- `python3 -m py_compile bridge/hermes_image_bridge.py scripts/benchmark_routing.py scripts/test-artifact-manifest.py onboarding/server.py`: PASS
- `python3 scripts/benchmark_routing.py`: PASS - 56/56, F1=1.00, including virtual model cases
- `python3 scripts/test-artifact-manifest.py`: PASS
- Lightweight Bridge endpoint test with temporary host root:
  - `GET /v1/models`: PASS - returned `opendeepseek-auto`, `opendeepseek-fast`, `opendeepseek-agent`, `opendeepseek-deepwork`, `hermes-agent`, `deepseek-v4-flash`
  - `GET /runs`: PASS
  - `GET /artifacts`: PASS
- `docker compose config`: PASS
- `docker compose -f docker-compose.cn.yml config`: PASS
- `./setup.sh verify`: PASS - 0 errors, 4 warnings because Docker/OpenDeepSeek runtime is intentionally stopped after reboot
- `scripts/goal-check.sh`: PASS - 23 passed, 0 failed, 2 skipped
- `scripts/release-gate.sh`: PASS - 26 passed, 0 failed, 0 warnings, 1 skipped

Decisions:

- Bridge now owns `/v1/models` and exposes product modes directly to Open WebUI.
- `opendeepseek-auto` preserves automatic routing.
- `opendeepseek-fast` forces lightweight DeepSeek path unless image attachments require Hermes/OCR.
- `opendeepseek-agent` forces Hermes.
- `opendeepseek-deepwork` forces Hermes with the existing high output budget.
- Open WebUI defaults now prefer `opendeepseek-auto` and pin the four product modes.
- Minimal run state endpoints exist: `GET /runs`, `GET /runs/<run_id>`, `POST /runs/<run_id>/stop`. First version records status/stop requests but does not kill an already-sent upstream request.
- `hermes-agent` remains listed as a compatibility model.

Risks:

- Run stop is a control-plane placeholder, not hard cancellation.
- Open WebUI may persist old default model settings in its database after first launch; users may need Admin UI reset or future migration tooling.
- Full runtime smoke-test was not run because Docker daemon remains intentionally stopped.

Next recommended goal:

```text
/goal 实现 M6：发布材料。更新 README、docs/zh-CN、演示脚本和 release checklist，明确 China Ready 哪些已完成、哪些需要云账号发布；准备公开发布前人工卡口，不 push、不 merge、不 tag、不上传镜像或 OSS/COS。
```

## 2026-05-06 - M6 Release Materials

Status: done

Changed files:

- `README.md`
- `docs/README.md`
- `docs/RELEASE-CHECKLIST.md`
- `docs/DEMO-SCRIPT-CN.md`
- `docs/zh-CN/README.md`
- `docs/zh-CN/screenshots/README.md`
- `docs/GOALS/STATUS.md`

Validation:

- `scripts/build-offline-bundle.sh --version 0.5.0-cn`: PASS - regenerated local ignored bundle and checksum under `dist/cn/`
- `python3 -m py_compile bridge/hermes_image_bridge.py onboarding/server.py scripts/benchmark_routing.py scripts/test-artifact-manifest.py`: PASS
- `python3 scripts/benchmark_routing.py`: PASS - 56/56, F1=1.00
- `python3 scripts/test-artifact-manifest.py`: PASS
- `./setup.sh verify`: PASS - 0 errors, 4 warnings because Docker/OpenDeepSeek runtime is intentionally stopped after reboot
- `scripts/goal-check.sh`: PASS - 23 passed, 0 failed, 2 skipped
- `scripts/release-gate.sh`: PASS - 26 passed, 0 failed, 0 warnings, 1 skipped

Decisions:

- README now states M0-M5 local productization is complete but cloud release actions still need maintainer approval.
- Chinese docs now have a dedicated index under `docs/zh-CN/README.md`.
- Demo script focuses on real product proof: Portal, modes, Key, fast chat, Hermes Agent file generation, artifact card, China install path.
- Screenshot placeholders are documented without committing fake screenshots.
- Release checklist now includes Artifact Manifest, product modes, offline bundle, screenshot placeholders, and explicit manual approval boundaries.

Remaining manual release gates:

- Start Docker / OrbStack and run `scripts/release-gate.sh --full`.
- Sync GitHub to Gitee/GitCode.
- Push domestic images after `docker login` and explicit approval.
- Upload offline bundles to OSS/COS/CDN.
- Fill real commit, URLs, checksums, and image digests in `release-cn.json`.
- Tag release, merge PR, or publish GitHub/Gitee release only after human approval.

Next recommended goal:

```text
/goal 执行最终本地收尾：检查 git diff、确认没有 .env/密钥/大文件入库，运行最终 goal-check/release-gate，生成一份 FINAL-HANDOVER.md。不要启动 Docker，不 push，不 merge，不 tag。
```

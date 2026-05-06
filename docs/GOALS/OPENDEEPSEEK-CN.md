# OpenDeepSeek CN Goals

Last updated: 2026-05-06

This file is the milestone spec for turning OpenDeepSeek from a working Agent stack into a publishable China-ready product.

## North Star

> OpenDeepSeek CN: Chinese-first, China-network-ready, one-click installable, real Agent, polished entry experience.

The project already proved the core chain:

- ordinary chat routes to DeepSeek V4 Flash lightweight path
- real Agent tasks route to Hermes
- `/host` file writes work
- image/OCR bridge works
- realtime progress stream works
- OpenWebUI native tool calls are preserved
- smoke-test has passed

The goal is no longer "prove the architecture can work". The goal is productization.

## Non-Goals

- Do not rebuild Open WebUI.
- Do not deeply rebrand Open WebUI or remove attribution.
- Do not introduce a new heavy frontend framework unless a milestone explicitly approves it.
- Do not publish cloud credentials, API keys, or registry credentials.
- Do not push images, upload OSS/COS assets, merge PRs, or tag releases without explicit user approval.

## Milestones

### M0: Release Gate

Goal: make the current international/developer release safe to merge and publish.

Scope:

- Add `scripts/release-gate.sh`.
- Add or update `docs/RELEASE-CHECKLIST.md`.
- Check README/install/setup/compose/bridge consistency with Smart Bridge architecture.
- Aggregate:
  - `python3 scripts/benchmark_routing.py`
  - `./setup.sh verify`
  - `bash scripts/smoke-test.sh`
  - `docker compose config`
  - model name check for `deepseek-v4-flash`
  - public exposure safety check

Validation:

```bash
bash -n scripts/release-gate.sh
scripts/release-gate.sh
```

Done when:

- release-gate produces Chinese-readable pass/fail output
- existing one-click install path is not broken
- `docs/GOALS/STATUS.md` records validation results

### M1: China Installer And Network Adaptation

Goal: make China installation a first-class path.

Scope:

- `install-cn.sh`
- `install-cn.ps1`
- `docker-compose.cn.yml`
- `.env.example.cn`
- `scripts/check-network-cn.sh`
- `docs/zh-CN/04-国内网络问题.md`
- `docs/zh-CN/05-离线安装.md`
- README China install entry

Requirements:

- Do not require China users to start from GitHub raw.
- Support Gitee/GitCode/OSS/COS source configuration.
- Detect GitHub, Gitee, GitCode, OSS/COS, DeepSeek API, domestic container registry, PyPI mirror, npm mirror.
- If domestic image pull fails, point users to offline bundle.
- CN compose must not expose Hermes/Bridge publicly by default.
- CN env defaults to Chinese, DeepSeek V4 Flash, and product modes.
- No real keys or cloud credentials.

Validation:

```bash
bash -n install-cn.sh scripts/check-network-cn.sh
docker compose -f docker-compose.cn.yml config
./setup.sh verify
python3 scripts/benchmark_routing.py
```

### M2: Domestic Images And Offline Bundles

Goal: create the publish skeleton for domestic images and offline bundles.

Scope:

- `release-cn.json`
- `scripts/sync-images-cn.sh`
- `scripts/build-offline-bundle.sh`
- `scripts/checksums.sh`
- `docs/zh-CN/00-我应该下载哪个版本.md`
- `docs/zh-CN/离线包发布流程.md`

Requirements:

- Use environment variables for registry/account configuration.
- Default naming pattern:

```text
registry.cn-hangzhou.aliyuncs.com/opendeepseek/...
```

- Generate SHA256 checksums.
- Do not perform real registry pushes unless explicitly approved.

Validation:

```bash
bash -n scripts/sync-images-cn.sh scripts/build-offline-bundle.sh scripts/checksums.sh
./setup.sh verify
```

### M3: Chinese Portal And Onboarding 2.0

Goal: give ordinary Chinese users a polished entry point before Open WebUI.

Scope:

- `portal/` or onboarding upgrade
- Chinese homepage
- service status cards
- API Key setup entry
- file permission explanation
- diagnostics entry
- artifacts entry placeholder
- `docs/zh-CN/06-填写DeepSeek-Key.md`
- `docs/zh-CN/07-文件权限说明.md`

Requirements:

- Do not modify Open WebUI source branding.
- Mobile-friendly.
- Explain "ordinary questions are fast; real tasks automatically switch to Agent".
- No large frontend framework by default.

Validation:

```bash
python3 -m py_compile onboarding/server.py
./setup.sh verify
```

### M4: Artifact Manifest And Preview

Goal: make generated files visible as products, not mysterious `/host` paths.

Scope:

- `docs/ARTIFACT-MANIFEST.md`
- artifact manifest schema
- first read/write implementation in Bridge or control sidecar
- read-only `/artifacts/<task_id>/...` preview
- Chinese artifact card markdown appended to responses
- smoke-test artifact check

Security:

- Only serve files under `OpenDeepSeek-Outputs`.
- Block directory traversal.
- Never serve `.env`, hidden files, keys, or arbitrary `/host`.

Validation:

```bash
python3 scripts/benchmark_routing.py
./setup.sh verify
bash scripts/smoke-test.sh
```

### M5: OpenWebUI/Hermes Fusion

Goal: expose productized virtual models and lay groundwork for long task control.

Scope:

- `/v1/models` exposes:
  - `opendeepseek-auto`
  - `opendeepseek-fast`
  - `opendeepseek-agent`
  - `opendeepseek-deepwork`
- Routing supports auto/fast/agent/deepwork.
- Default/pinned model config updated.
- Initial run_id/status/stop abstraction.
- Preserve OpenWebUI native tools.

Validation:

```bash
python3 scripts/benchmark_routing.py
./setup.sh verify
bash scripts/smoke-test.sh
```

### M6: Release Materials

Goal: prepare public release assets and user-facing explanation.

Scope:

- README update
- `docs/zh-CN/` completion
- demo script
- release checklist
- CN install screenshots or placeholders
- video outline for data flywheel + Agent demo

Validation:

```bash
scripts/goal-check.sh
```

## Milestone Order

Recommended order:

```text
M0 → M1 → M2 → M3 → M4 → M5 → M6
```

M0 can be skipped only if the user explicitly wants to start with China installer work first.

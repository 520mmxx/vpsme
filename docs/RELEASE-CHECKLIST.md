# OpenDeepSeek Release Checklist

Last updated: 2026-05-06

Use this checklist before merging or publishing OpenDeepSeek. The current project has two release tracks:

- international/developer release: existing GitHub-based one-click path
- China Ready release: future `OpenDeepSeek CN` path described in `docs/OPENDEEPSEEK-CN-ROADMAP.md`

## 1. Release Gate Commands

Fast preflight:

```bash
scripts/release-gate.sh
```

Full release gate, after starting the local stack:

```bash
docker compose up -d
scripts/release-gate.sh --full
```

Goal workflow validation:

```bash
scripts/goal-check.sh
```

M0-M5 local productization preflight:

```bash
python3 -m py_compile bridge/hermes_image_bridge.py onboarding/server.py
python3 scripts/benchmark_routing.py
python3 scripts/test-artifact-manifest.py
scripts/sync-images-cn.sh
scripts/build-offline-bundle.sh --version 0.5.0-cn
```

## 2. Required Automated Checks

The release gate must pass:

- shell syntax checks for release/install/setup/smoke scripts
- `docker compose config`
- `python3 scripts/benchmark_routing.py`
- `./setup.sh verify`
- model default check: `deepseek-v4-flash`
- Hermes output budget check: `HERMES_AGENT_MAX_TOKENS >= 32768`
- public exposure check
- Bridge image/OCR adaptation guard
- Bridge `Accept-Encoding: identity` regression guard

Before an actual release, full mode must also pass:

- `bash scripts/smoke-test.sh`

## 3. Manual UI Checks

Open `http://localhost:3000` and verify:

- model list shows `opendeepseek-auto`, `opendeepseek-fast`, `opendeepseek-agent`, `opendeepseek-deepwork`
- ordinary chat replies quickly
- `/agent` file task creates a real file under `OpenDeepSeek-Outputs`
- realtime/news task shows Chinese progress before final content
- image upload does not produce API errors
- OpenWebUI native tools still work when the request is not an Agent task
- generated file replies include user-findable local paths
- generated file replies include an OpenDeepSeek artifact card
- artifact preview opens through `http://localhost:8770/artifacts/...`

## 4. Security Checks

Do not release if:

- real API keys or tokens are in git diff
- `.env` is staged
- `BIND_HOST=0.0.0.0` with `WEBUI_AUTH=false`
- Hermes or Bridge are publicly exposed by default
- artifact preview port is bound to `0.0.0.0` instead of `127.0.0.1`
- `HERMES_AGENT_MAX_TOKENS` was lowered
- DeepSeek text path can receive raw `image_url`
- smoke-test was removed or weakened

## 5. PR/Main Checks

Before telling users to run the public one-liner:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/mouxue56-debug/opendeepseek/main/install.sh)
```

Confirm:

- the intended PR branch is merged into `main`
- GitHub Actions are green
- `README.md` and `docs/ONE-CLICK.md` describe the same install path
- `install.sh` still works for international users
- China-specific paths are clearly marked as future or CN-specific until the CN assets exist

## 6. China Ready Release Notes

For `v0.5.0-cn` and later, additionally require:

- `install-cn.sh`
- `install-cn.ps1`
- `docker-compose.cn.yml`
- `.env.example.cn`
- `release-cn.json`
- `scripts/sync-images-cn.sh` dry-run reviewed
- `scripts/build-offline-bundle.sh` generated local package
- `scripts/checksums.sh` generated checksum
- domestic image registry tags published, or clearly marked as placeholders
- offline bundle checksum filled into `release-cn.json`
- `docs/zh-CN/` user-facing install docs
- network diagnostics for Gitee/GitCode/OSS/COS/DeepSeek/API mirrors
- screenshots or placeholders under `docs/zh-CN/screenshots/`

Do not perform these automatically without explicit approval:

- push Docker images to ACR/TCR
- upload files to OSS/COS/CDN
- write cloud AK/SK or registry credentials
- tag release
- merge PR to main
- publish GitHub/Gitee release assets

Do not claim China Ready until users can install without GitHub raw as a single point of failure.

## 7. Rollback Notes

If release validation fails:

1. Do not merge.
2. Keep the failing logs.
3. Fix only the failing area.
4. Re-run the failing command.
5. Update `docs/GOALS/STATUS.md` with the failure and resolution.

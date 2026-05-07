#!/usr/bin/env bash
# Push current HEAD to the configured Gitee mirror and verify raw installer.
# Never pass tokens on the command line. Use GITEE_TOKEN in the environment.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

GITEE_USERNAME="${GITEE_USERNAME:-luoxueai}"
GITEE_REPO_URL="${GITEE_REPO_URL:-https://gitee.com/luoxueai/opendeepseek.git}"
GITEE_RAW_URL="${GITEE_RAW_URL:-https://gitee.com/luoxueai/opendeepseek/raw/main/install-cn.sh}"
TARGET_BRANCH="${GITEE_BRANCH:-main}"
VERIFY_ONLY=false
export GITEE_USERNAME

if [[ "${1:-}" == "--verify-only" ]]; then
  VERIFY_ONLY=true
elif [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  cat <<'EOF'
OpenDeepSeek Gitee sync helper

Usage:
  GITEE_TOKEN=*** ./scripts/sync-gitee.sh
  ./scripts/sync-gitee.sh --verify-only

Environment:
  GITEE_USERNAME  Gitee username, default luoxueai
  GITEE_TOKEN     Gitee personal access token, required unless --verify-only
  GITEE_REPO_URL  Mirror repo URL
  GITEE_RAW_URL   Raw install-cn.sh URL to verify
GITEE_BRANCH    Target branch, default main
EOF
  exit 0
fi

log() { printf '%s\n' "ℹ️  $*"; }
ok() { printf '%s\n' "✅ $*"; }
die() { printf '%s\n' "❌ $*" >&2; exit 1; }

head_sha="$(git rev-parse HEAD)"

if [[ "$VERIFY_ONLY" != "true" ]]; then
  [[ -n "${GITEE_TOKEN:-}" ]] || die "缺少 GITEE_TOKEN。请用环境变量传入，不要写进文件。"
  export GITEE_TOKEN
  askpass="$(mktemp)"
  cleanup() { rm -f "$askpass"; }
  trap cleanup EXIT
  cat >"$askpass" <<'SH'
#!/bin/sh
case "$1" in
  *Username*) printf '%s\n' "$GITEE_USERNAME" ;;
  *Password*) printf '%s\n' "$GITEE_TOKEN" ;;
  *) printf '\n' ;;
esac
SH
  chmod 700 "$askpass"
  log "推送当前 HEAD 到 Gitee ${TARGET_BRANCH}..."
  GIT_ASKPASS="$askpass" GIT_TERMINAL_PROMPT=0 git push "$GITEE_REPO_URL" "HEAD:${TARGET_BRANCH}"
fi

log "校验 Gitee branch..."
remote_sha="$(git ls-remote "$GITEE_REPO_URL" "refs/heads/${TARGET_BRANCH}" | awk '{print $1}')"
[[ -n "$remote_sha" ]] || die "Gitee ${TARGET_BRANCH} 不存在或不可读：${GITEE_REPO_URL}"
[[ "$remote_sha" == "$head_sha" ]] || die "Gitee 未同步到当前 HEAD：local=${head_sha} remote=${remote_sha}"
ok "Gitee ${TARGET_BRANCH} = ${remote_sha:0:7}"

log "校验 Gitee raw installer..."
tmp="$(mktemp)"
if ! curl -L -sS -o "$tmp" --connect-timeout 8 --max-time 30 "$GITEE_RAW_URL" 2>/dev/null \
  || ! grep -q "OpenDeepSeek CN smart installer" "$tmp"; then
  code="$(curl -L -sS -o /dev/null -w '%{http_code}' --connect-timeout 8 --max-time 30 "$GITEE_RAW_URL" 2>/dev/null || true)"
  rm -f "$tmp"
  die "Gitee raw install-cn.sh 不可用：HTTP ${code:-000} ${GITEE_RAW_URL}"
fi
rm -f "$tmp"
ok "Gitee raw install-cn.sh 可访问"

#!/usr/bin/env bash
# OpenDeepSeek release gate.
#
# Default mode is safe for a stopped local stack: it runs static/offline checks,
# docker compose config, setup verification, and routing benchmark. Use --full
# or OPDS_RELEASE_FULL=true before an actual release to also run smoke-test.

set -u
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT_DIR}" || exit 1

FULL="${OPDS_RELEASE_FULL:-false}"
if [[ "${1:-}" == "--full" ]]; then
  FULL="true"
elif [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  cat <<'EOF'
OpenDeepSeek release gate

Usage:
  scripts/release-gate.sh          # static/offline release preflight
  scripts/release-gate.sh --full   # also run scripts/smoke-test.sh

Environment:
  OPDS_RELEASE_FULL=true           # same as --full
EOF
  exit 0
fi

PASS=0
FAIL=0
WARN=0
SKIP=0

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

ok() {
  echo -e "${GREEN}通过${NC} $1"
  PASS=$((PASS + 1))
}

fail() {
  echo -e "${RED}失败${NC} $1"
  FAIL=$((FAIL + 1))
}

warn() {
  echo -e "${YELLOW}警告${NC} $1"
  WARN=$((WARN + 1))
}

skip() {
  echo -e "${YELLOW}跳过${NC} $1"
  SKIP=$((SKIP + 1))
}

info() {
  echo -e "${BLUE}检查${NC} $1"
}

run_required() {
  local label="$1"
  shift
  info "${label}"
  if "$@"; then
    ok "${label}"
  else
    fail "${label}"
  fi
}

require_file() {
  local file="$1"
  if [[ -f "${file}" ]]; then
    ok "文件存在：${file}"
  else
    fail "文件缺失：${file}"
  fi
}

env_value() {
  local file="$1"
  local key="$2"
  [[ -f "${file}" ]] || return 0
  grep -m1 -E "^${key}=" "${file}" | cut -d'=' -f2- | tr -d '[:space:]"'"'"'' || true
}

check_default_model() {
  local model
  model="$(env_value .env.example DEFAULT_MODEL)"
  if [[ "${model}" == "deepseek-v4-flash" ]]; then
    ok ".env.example 默认模型是 deepseek-v4-flash"
  else
    fail ".env.example 默认模型不是 deepseek-v4-flash：${model:-<empty>}"
  fi

  if grep -q 'DEFAULT_MODEL=${DEFAULT_MODEL:-deepseek-v4-flash}' docker-compose.yml \
    && grep -q 'DEFAULT_MODEL="deepseek-v4-flash"' setup.sh; then
    ok "docker-compose/setup 默认模型 fallback 指向 deepseek-v4-flash"
  else
    fail "docker-compose/setup 默认模型 fallback 不一致"
  fi

  if [[ -f .env ]]; then
    local local_model
    local_model="$(env_value .env DEFAULT_MODEL)"
    case "${local_model}" in
      deepseek-v4-flash|deepseek-v4-pro)
        ok ".env 当前模型受支持：${local_model}"
        ;;
      deepseek-chat|deepseek-reasoner)
        warn ".env 使用旧兼容模型名：${local_model}，发布默认仍应使用 deepseek-v4-flash"
        ;;
      "")
        warn ".env 未设置 DEFAULT_MODEL，将依赖默认值"
        ;;
      *)
        fail ".env 当前模型不受支持：${local_model}"
        ;;
    esac
  fi
}

check_token_budget() {
  local example_budget
  example_budget="$(env_value .env.example HERMES_AGENT_MAX_TOKENS)"
  if [[ "${example_budget}" =~ ^[0-9]+$ ]] && [[ "${example_budget}" -ge 32768 ]]; then
    ok ".env.example Hermes 输出预算保持高位：${example_budget}"
  else
    fail ".env.example HERMES_AGENT_MAX_TOKENS 过低或缺失：${example_budget:-<empty>}"
  fi

  if [[ -f .env ]]; then
    local local_budget
    local_budget="$(env_value .env HERMES_AGENT_MAX_TOKENS)"
    if [[ "${local_budget}" =~ ^[0-9]+$ ]] && [[ "${local_budget}" -ge 32768 ]]; then
      ok ".env Hermes 输出预算保持高位：${local_budget}"
    else
      fail ".env HERMES_AGENT_MAX_TOKENS 过低或缺失：${local_budget:-<empty>}"
    fi
  fi
}

check_public_safety() {
  if grep -qE '0\.0\.0\.0:[0-9]+:' docker-compose.yml; then
    fail "docker-compose.yml 存在硬编码公网绑定"
  else
    ok "docker-compose.yml 没有硬编码公网绑定"
  fi

  if grep -q '\${BIND_HOST:-127.0.0.1}:3000:8080' docker-compose.yml \
    && grep -q '\${BIND_HOST:-127.0.0.1}:8642:8642' docker-compose.yml; then
    ok "OpenWebUI/Hermes 默认绑定 127.0.0.1"
  else
    fail "OpenWebUI/Hermes 默认绑定不是 127.0.0.1"
  fi

  if [[ -f .env ]]; then
    local bind_host webui_auth
    bind_host="$(env_value .env BIND_HOST)"
    webui_auth="$(env_value .env WEBUI_AUTH)"
    bind_host="${bind_host:-127.0.0.1}"
    webui_auth="${webui_auth:-false}"
    if [[ "${bind_host}" == "0.0.0.0" && "${webui_auth}" != "true" ]]; then
      fail ".env 当前配置是 BIND_HOST=0.0.0.0 且 WEBUI_AUTH!=true，不能发布"
    else
      ok ".env 未命中无认证公网暴露组合"
    fi
  fi
}

check_image_bridge_safety() {
  if grep -q 'def sanitize_payload' bridge/hermes_image_bridge.py \
    && grep -q 'image_url' bridge/hermes_image_bridge.py \
    && grep -q 'direct\["model"\] = DEFAULT_MODEL' bridge/hermes_image_bridge.py; then
    ok "Bridge 保留 image_url 本地解析与 DeepSeek 模型归一化逻辑"
  else
    fail "Bridge 图片/DeepSeek 适配保护缺失"
  fi

  if grep -q 'headers\["Accept-Encoding"\] = "identity"' bridge/hermes_image_bridge.py; then
    ok "Bridge 保留 OpenWebUI 压缩响应修复"
  else
    fail "Bridge 缺少 Accept-Encoding=identity 修复"
  fi
}

check_one_click_docs() {
  if grep -q 'raw.githubusercontent.com/mouxue56-debug/opendeepseek/main/install.sh' README.md \
    && [[ -f install.sh ]] \
    && [[ -f docs/ONE-CLICK.md ]]; then
    ok "国际一键安装入口仍存在"
  else
    fail "国际一键安装入口缺失或文档不一致"
  fi
}

echo "OpenDeepSeek 发布闸门"
echo "root: ${ROOT_DIR}"
echo "full smoke-test: ${FULL}"
echo

require_file README.md
require_file install.sh
require_file setup.sh
require_file docker-compose.yml
require_file bridge/hermes_image_bridge.py
require_file scripts/benchmark_routing.py
require_file scripts/smoke-test.sh
require_file .env.example

run_required "release-gate 语法" bash -n scripts/release-gate.sh
run_required "install.sh 语法" bash -n install.sh
run_required "setup.sh 语法" bash -n setup.sh
run_required "smoke-test 语法" bash -n scripts/smoke-test.sh

check_one_click_docs
check_default_model
check_token_budget
check_public_safety
check_image_bridge_safety

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  run_required "docker compose config" bash -c 'docker compose config >/tmp/opds-release-compose.txt'
else
  fail "docker compose 不可用"
fi

run_required "离线路由基准" python3 scripts/benchmark_routing.py

if [[ -x setup.sh ]]; then
  run_required "配置验证 ./setup.sh verify" ./setup.sh verify
else
  fail "setup.sh 不可执行"
fi

if [[ "${FULL}" == "true" ]]; then
  run_required "完整 smoke-test" bash scripts/smoke-test.sh
else
  skip "完整 smoke-test 未运行；正式发布前执行：scripts/release-gate.sh --full"
fi

echo
echo "结果：${PASS} 通过，${FAIL} 失败，${WARN} 警告，${SKIP} 跳过"

if [[ "${FAIL}" -ne 0 ]]; then
  echo "发布闸门未通过。请先修复失败项。"
  exit 1
fi

if [[ "${SKIP}" -ne 0 ]]; then
  echo "发布预检通过，但仍有跳过项。真正发布前请跑 full gate。"
else
  echo "发布闸门通过。"
fi

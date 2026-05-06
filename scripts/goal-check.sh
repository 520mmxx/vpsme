#!/usr/bin/env bash
# Aggregate validation for OpenDeepSeek goal-style milestones.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT_DIR}" || exit 1

PASS=0
FAIL=0
SKIP=0

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

ok() {
  echo -e "${GREEN}PASS${NC} $1"
  PASS=$((PASS + 1))
}

fail() {
  echo -e "${RED}FAIL${NC} $1"
  FAIL=$((FAIL + 1))
}

skip() {
  echo -e "${YELLOW}SKIP${NC} $1"
  SKIP=$((SKIP + 1))
}

info() {
  echo -e "${BLUE}INFO${NC} $1"
}

run_required() {
  local label="$1"
  shift
  info "$label"
  if "$@"; then
    ok "$label"
  else
    fail "$label"
  fi
}

run_optional() {
  local label="$1"
  shift
  info "$label"
  if "$@"; then
    ok "$label"
  else
    skip "$label"
  fi
}

echo "OpenDeepSeek goal check"
echo "root: ${ROOT_DIR}"
echo

run_required "goal-check shell syntax" bash -n scripts/goal-check.sh

if [[ -f install.sh ]]; then
  run_required "install.sh shell syntax" bash -n install.sh
fi

if [[ -f install-cn.sh ]]; then
  run_required "install-cn.sh shell syntax" bash -n install-cn.sh
fi

if [[ -f setup.sh ]]; then
  run_required "setup.sh shell syntax" bash -n setup.sh
fi

while IFS= read -r script; do
  run_required "${script} shell syntax" bash -n "${script}"
done < <(find scripts -maxdepth 1 -type f -name '*.sh' | sort)

if command -v shellcheck >/dev/null 2>&1; then
  run_required "shellcheck shell scripts" shellcheck install.sh setup.sh scripts/*.sh
else
  skip "shellcheck not installed"
fi

if [[ -f scripts/benchmark_routing.py ]]; then
  run_required "offline routing benchmark" python3 scripts/benchmark_routing.py
fi

if [[ -f scripts/test-artifact-manifest.py ]]; then
  run_required "artifact manifest offline test" python3 scripts/test-artifact-manifest.py
fi

if [[ -f scripts/test-provider-config.py ]]; then
  run_required "provider config offline test" python3 scripts/test-provider-config.py
fi

if [[ -x setup.sh ]]; then
  run_optional "setup.sh verify" ./setup.sh verify
else
  skip "setup.sh is not executable"
fi

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  run_optional "docker compose config" bash -c 'docker compose config >/tmp/opds-goal-compose.txt'
  if [[ -f docker-compose.cn.yml ]]; then
    run_optional "docker compose cn config" bash -c 'docker compose -f docker-compose.cn.yml config >/tmp/opds-goal-compose-cn.txt'
  fi
else
  skip "docker compose unavailable"
fi

if [[ "${OPDS_GOAL_FULL:-false}" == "true" ]]; then
  if [[ -f scripts/smoke-test.sh ]]; then
    run_required "full smoke-test" bash scripts/smoke-test.sh
  else
    fail "scripts/smoke-test.sh missing"
  fi
else
  skip "full smoke-test disabled; set OPDS_GOAL_FULL=true to run it"
fi

echo
echo "Result: ${PASS} passed, ${FAIL} failed, ${SKIP} skipped"

if [[ "${FAIL}" -ne 0 ]]; then
  exit 1
fi

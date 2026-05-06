#!/usr/bin/env bash
set -euo pipefail

ROUNDS="${1:-10}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

run_round() {
  local round="$1"
  echo "========== OpenDeepSeek debug round ${round}/${ROUNDS} =========="
  bash -n setup.sh install.sh install-cn.sh scripts/check-network-cn.sh scripts/goal-check.sh scripts/release-gate.sh scripts/debug-rounds.sh
  python3 -m py_compile bridge/hermes_image_bridge.py onboarding/server.py scripts/verify_config.py scripts/doctor.py scripts/test-provider-config.py
  python3 -m json.tool config/providers.example.json >/dev/null
  python3 scripts/test-provider-config.py
  python3 scripts/benchmark_routing.py
  python3 scripts/test-artifact-manifest.py
  docker compose config -q
  docker compose -f docker-compose.cn.yml config -q
  ./setup.sh verify
}

for round in $(seq 1 "$ROUNDS"); do
  run_round "$round"
done

echo "PASS: ${ROUNDS} debug round(s)"

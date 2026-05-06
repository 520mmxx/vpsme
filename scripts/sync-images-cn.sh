#!/usr/bin/env bash
# Prepare or publish OpenDeepSeek CN images.
#
# Default mode is a dry-run. Real registry pushes require:
#   scripts/sync-images-cn.sh --push
#   OPDS_CONFIRM_PUSH=I_UNDERSTAND
#   docker login to the target registry

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

OPDS_VERSION="${OPDS_VERSION:-0.5.0-cn}"
OPDS_IMAGE_REGISTRY="${OPDS_IMAGE_REGISTRY:-registry.cn-hangzhou.aliyuncs.com/opendeepseek}"
OPENWEBUI_SOURCE="${OPENWEBUI_SOURCE:-ghcr.io/open-webui/open-webui:0.9.2}"
HERMES_SOURCE="${HERMES_SOURCE:-nousresearch/hermes-agent:v2026.4.23}"
SEARXNG_SOURCE="${SEARXNG_SOURCE:-searxng/searxng:2026.4.28-ed5955a5c}"
OPENWEBUI_VERSION="${OPENWEBUI_VERSION:-0.9.2-opds-cn}"
HERMES_VERSION="${HERMES_VERSION:-2026.4.23-opds-cn}"
SEARXNG_VERSION="${SEARXNG_VERSION:-2026.4.28-opds-cn}"
HERMES_BRIDGE_VERSION="${HERMES_BRIDGE_VERSION:-${OPDS_VERSION}}"
DRY_RUN=true
PUSH=false

usage() {
  cat <<'EOF'
Prepare or publish OpenDeepSeek CN images.

Usage:
  scripts/sync-images-cn.sh
  scripts/sync-images-cn.sh --push

Environment:
  OPDS_IMAGE_REGISTRY    target registry, default registry.cn-hangzhou.aliyuncs.com/opendeepseek
  OPDS_VERSION           OpenDeepSeek CN version, default 0.5.0-cn
  OPENWEBUI_SOURCE       upstream Open WebUI image
  HERMES_SOURCE          upstream Hermes image
  SEARXNG_SOURCE         upstream SearXNG image
  OPDS_CONFIRM_PUSH      must be I_UNDERSTAND for --push

Default mode prints the docker commands only. It never pushes images.
EOF
}

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=true
      PUSH=false
      shift
      ;;
    --push)
      DRY_RUN=false
      PUSH=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

target_image() {
  local name="$1"
  local tag="$2"
  printf '%s/%s:%s\n' "$OPDS_IMAGE_REGISTRY" "$name" "$tag"
}

run_cmd() {
  if [[ "$DRY_RUN" == "true" ]]; then
    printf '+'
    printf ' %q' "$@"
    printf '\n'
  else
    "$@"
  fi
}

require_docker() {
  command -v docker >/dev/null 2>&1 || { echo "Missing docker" >&2; exit 1; }
  docker info >/dev/null 2>&1 || { echo "Docker daemon is not running" >&2; exit 1; }
}

sync_external_image() {
  local source="$1"
  local target="$2"
  echo
  echo "Image: $source -> $target"
  run_cmd docker pull "$source"
  run_cmd docker tag "$source" "$target"
  if [[ "$PUSH" == "true" ]]; then
    run_cmd docker push "$target"
  fi
}

build_bridge_image() {
  local target="$1"
  echo
  echo "Image: local bridge -> $target"
  run_cmd docker build -t "$target" "$ROOT_DIR/bridge"
  if [[ "$PUSH" == "true" ]]; then
    run_cmd docker push "$target"
  fi
}

main() {
  echo "OpenDeepSeek CN image sync"
  echo "registry: $OPDS_IMAGE_REGISTRY"
  echo "version:  $OPDS_VERSION"
  echo "mode:     $([[ "$DRY_RUN" == "true" ]] && echo dry-run || echo push)"

  if [[ "$PUSH" == "true" && "${OPDS_CONFIRM_PUSH:-}" != "I_UNDERSTAND" ]]; then
    echo "Refusing to push. Set OPDS_CONFIRM_PUSH=I_UNDERSTAND after docker login." >&2
    exit 1
  fi

  if [[ "$DRY_RUN" != "true" ]]; then
    require_docker
  fi

  sync_external_image "$OPENWEBUI_SOURCE" "$(target_image open-webui "$OPENWEBUI_VERSION")"
  sync_external_image "$HERMES_SOURCE" "$(target_image hermes "$HERMES_VERSION")"
  sync_external_image "$SEARXNG_SOURCE" "$(target_image searxng "$SEARXNG_VERSION")"
  build_bridge_image "$(target_image hermes-bridge "$HERMES_BRIDGE_VERSION")"

  echo
  echo "CN image targets:"
  echo "- $(target_image open-webui "$OPENWEBUI_VERSION")"
  echo "- $(target_image hermes "$HERMES_VERSION")"
  echo "- $(target_image searxng "$SEARXNG_VERSION")"
  echo "- $(target_image hermes-bridge "$HERMES_BRIDGE_VERSION")"
}

main "$@"

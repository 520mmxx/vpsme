#!/usr/bin/env bash
# Build OpenDeepSeek CN offline release bundles.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
VERSION="${OPDS_VERSION:-0.5.0-cn}"
DIST_DIR="${OPDS_CN_DIST_DIR:-${ROOT_DIR}/dist/cn}"
INCLUDE_IMAGES=false
ALLOW_MISSING_IMAGES=false
WORK_DIR=""

cleanup() {
  if [[ -n "${WORK_DIR:-}" && -d "$WORK_DIR" ]]; then
    rm -rf "$WORK_DIR"
  fi
}
trap cleanup EXIT

usage() {
  cat <<'EOF'
Build OpenDeepSeek CN offline bundles.

Usage:
  scripts/build-offline-bundle.sh
  scripts/build-offline-bundle.sh --version 0.5.0-cn --out dist/cn
  scripts/build-offline-bundle.sh --with-images

Options:
  --version <v>       release version, default OPDS_VERSION or 0.5.0-cn
  --out <dir>         output directory, default dist/cn
  --with-images       also docker save CN images into a tar.zst/tar.gz bundle
  --allow-missing     with --with-images, skip missing local images instead of failing

This script does not upload anything. It only writes local artifacts.
EOF
}

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --version)
      [[ "$#" -ge 2 ]] || { echo "Missing value for --version" >&2; exit 2; }
      VERSION="$2"
      shift 2
      ;;
    --out)
      [[ "$#" -ge 2 ]] || { echo "Missing value for --out" >&2; exit 2; }
      DIST_DIR="$2"
      shift 2
      ;;
    --with-images)
      INCLUDE_IMAGES=true
      shift
      ;;
    --allow-missing)
      ALLOW_MISSING_IMAGES=true
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

detect_os() {
  case "$(uname -s)" in
    Darwin) echo "macos" ;;
    Linux) echo "linux" ;;
    MINGW*|MSYS*|CYGWIN*) echo "windows" ;;
    *) echo "unknown" ;;
  esac
}

detect_arch() {
  case "$(uname -m)" in
    x86_64|amd64) echo "amd64" ;;
    arm64|aarch64) echo "arm64" ;;
    *) uname -m ;;
  esac
}

copy_tree() {
  local src="$1"
  local dst="$2"
  if command -v rsync >/dev/null 2>&1; then
    rsync -a "$src/" "$dst/" \
      --exclude '.git' \
      --exclude '.env' \
      --exclude '.claude' \
      --exclude '.planning' \
      --exclude 'dist' \
      --exclude 'benchmark-results' \
      --exclude 'agent-files/*' \
      --exclude 'debug-log.md' \
      --exclude 'debug-summary.md' \
      --exclude '.DS_Store' \
      --exclude '__pycache__' \
      --exclude '*.pyc' \
      --exclude '*.bak' \
      --exclude '*.tmp'
  else
    mkdir -p "$dst"
    (
      cd "$src"
      tar \
        --exclude='.git' \
        --exclude='.env' \
        --exclude='.claude' \
        --exclude='.planning' \
        --exclude='dist' \
        --exclude='benchmark-results' \
        --exclude='agent-files/*' \
        --exclude='.DS_Store' \
        --exclude='__pycache__' \
        -cf - .
    ) | (
      cd "$dst"
      tar -xf -
    )
  fi
}

make_zip() {
  local source_dir="$1"
  local zip_path="$2"
  if command -v zip >/dev/null 2>&1; then
    (
      cd "$(dirname "$source_dir")"
      zip -qr "$zip_path" "$(basename "$source_dir")"
    )
    echo "$zip_path"
  else
    echo "zip not found; skipping zip package" >&2
  fi
}

make_targz() {
  local source_dir="$1"
  local tar_path="$2"
  (
    cd "$(dirname "$source_dir")"
    tar -czf "$tar_path" "$(basename "$source_dir")"
  )
  echo "$tar_path"
}

image_names() {
  local registry="${OPDS_IMAGE_REGISTRY:-registry.cn-hangzhou.aliyuncs.com/opendeepseek}"
  local openwebui="${OPENWEBUI_VERSION:-0.9.2-opds-cn}"
  local hermes="${HERMES_VERSION:-2026.4.23-opds-cn}"
  local searxng="${SEARXNG_VERSION:-2026.4.28-opds-cn}"
  local bridge="${HERMES_BRIDGE_VERSION:-${VERSION}}"
  printf '%s\n' \
    "${registry}/open-webui:${openwebui}" \
    "${registry}/hermes:${hermes}" \
    "${registry}/searxng:${searxng}" \
    "${registry}/hermes-bridge:${bridge}"
}

build_image_bundle() {
  local arch="$1"
  local output_base="${DIST_DIR}/opendeepseek-images-cn-v${VERSION}-${arch}.tar"
  local images=()
  local missing=()
  command -v docker >/dev/null 2>&1 || { echo "Missing docker; cannot build image bundle" >&2; exit 1; }
  docker info >/dev/null 2>&1 || { echo "Docker daemon is not running; cannot build image bundle" >&2; exit 1; }

  while IFS= read -r image; do
    if docker image inspect "$image" >/dev/null 2>&1; then
      images+=("$image")
    else
      missing+=("$image")
    fi
  done < <(image_names)

  if [[ "${#missing[@]}" -gt 0 ]]; then
    echo "Missing local images:" >&2
    printf '  %s\n' "${missing[@]}" >&2
    if [[ "$ALLOW_MISSING_IMAGES" != "true" ]]; then
      echo "Run scripts/sync-images-cn.sh first, or use --allow-missing." >&2
      exit 1
    fi
  fi

  if [[ "${#images[@]}" -eq 0 ]]; then
    echo "No local CN images available; skipping image bundle" >&2
    return 0
  fi

  docker save "${images[@]}" -o "$output_base"
  if command -v zstd >/dev/null 2>&1; then
    zstd -f "$output_base" -o "${output_base}.zst"
    rm -f "$output_base"
    echo "${output_base}.zst"
  else
    gzip -f "$output_base"
    echo "${output_base}.gz"
  fi
}

main() {
  local os arch package_name package_dir artifacts=()
  os="$(detect_os)"
  arch="$(detect_arch)"
  package_name="opendeepseek-cn-v${VERSION}-${os}-${arch}"
  WORK_DIR="$(mktemp -d)"
  package_dir="${WORK_DIR}/${package_name}"

  mkdir -p "$DIST_DIR" "$package_dir"

  echo "Building OpenDeepSeek CN bundle"
  echo "version: $VERSION"
  echo "target:  $os-$arch"
  echo "output:  $DIST_DIR"

  copy_tree "$ROOT_DIR" "$package_dir"
  chmod +x "$package_dir/install.sh" "$package_dir/install-cn.sh" "$package_dir/setup.sh" "$package_dir/OpenDeepSeek.command" 2>/dev/null || true
  find "$package_dir/scripts" -type f -name '*.sh' -exec chmod +x {} \; 2>/dev/null || true

  if [[ "$os" == "macos" || "$os" == "windows" ]]; then
    zip_artifact="$(make_zip "$package_dir" "${DIST_DIR}/${package_name}.zip" || true)"
    [[ -n "${zip_artifact:-}" ]] && artifacts+=("$zip_artifact")
  fi

  tar_artifact="$(make_targz "$package_dir" "${DIST_DIR}/${package_name}.tar.gz")"
  artifacts+=("$tar_artifact")

  if [[ "$INCLUDE_IMAGES" == "true" ]]; then
    image_artifact="$(build_image_bundle "$arch" || true)"
    [[ -n "${image_artifact:-}" ]] && artifacts+=("$image_artifact")
  else
    echo "Image bundle skipped. Use --with-images after CN images are present locally."
  fi

  "${ROOT_DIR}/scripts/checksums.sh" -o "${DIST_DIR}/checksums.txt" "${artifacts[@]}"

  echo
  echo "Artifacts:"
  for artifact in "${artifacts[@]}"; do
    echo "- $artifact"
  done
  echo "- ${DIST_DIR}/checksums.txt"
}

main "$@"

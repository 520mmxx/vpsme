#!/usr/bin/env bash
# Generate SHA256 checksums for release files.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
OUTPUT="${OPDS_CHECKSUMS_OUTPUT:-checksums.txt}"
TARGETS=()

usage() {
  cat <<'EOF'
Generate SHA256 checksums.

Usage:
  scripts/checksums.sh [-o checksums.txt] <file-or-directory> [...]

Examples:
  scripts/checksums.sh -o dist/cn/checksums.txt dist/cn/*.zip dist/cn/*.tar.gz
  scripts/checksums.sh -o dist/cn/checksums.txt dist/cn/v0.5.0
EOF
}

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    -o|--output)
      [[ "$#" -ge 2 ]] || { echo "Missing value for $1" >&2; exit 2; }
      OUTPUT="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      TARGETS+=("$1")
      shift
      ;;
  esac
done

if [[ "${#TARGETS[@]}" -eq 0 ]]; then
  usage >&2
  exit 2
fi

if command -v shasum >/dev/null 2>&1; then
  CHECKSUM_CMD=(shasum -a 256)
elif command -v sha256sum >/dev/null 2>&1; then
  CHECKSUM_CMD=(sha256sum)
else
  echo "Missing shasum or sha256sum" >&2
  exit 1
fi

abs_path() {
  local path="$1"
  local dir base
  dir="$(cd "$(dirname "$path")" && pwd -P)"
  base="$(basename "$path")"
  printf '%s/%s\n' "$dir" "$base"
}

collect_files() {
  local target="$1"
  if [[ -f "$target" ]]; then
    printf '%s\0' "$target"
  elif [[ -d "$target" ]]; then
    find "$target" -type f \
      ! -name '.DS_Store' \
      ! -name 'checksums.txt' \
      -print0
  else
    echo "Missing target: $target" >&2
    exit 1
  fi
}

mkdir -p "$(dirname "$OUTPUT")"
TMP_OUTPUT="$(mktemp "${OUTPUT}.tmp.XXXXXX")"
trap 'rm -f "$TMP_OUTPUT"' EXIT
: >"$TMP_OUTPUT"

OUTPUT_ABS="$(abs_path "$OUTPUT")"

for target in "${TARGETS[@]}"; do
  while IFS= read -r -d '' file; do
    file_abs="$(abs_path "$file")"
    [[ "$file_abs" == "$OUTPUT_ABS" ]] && continue
    "${CHECKSUM_CMD[@]}" "$file" >>"$TMP_OUTPUT"
  done < <(collect_files "$target")
done

sort "$TMP_OUTPUT" >"$OUTPUT"
echo "Wrote checksums: $OUTPUT"

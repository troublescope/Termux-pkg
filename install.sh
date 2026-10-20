#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail

REPOSITORY="troublescope/Termux-pkg"
INDEX_URL="https://github.com/${REPOSITORY}/releases/latest/download/release-index.tsv"

usage() {
  cat <<'EOF'
Install native Cloudflare Wrangler build made for Termux aarch64.

Usage:
  install.sh [wrangler]

Examples:
  install.sh
  install.sh wrangler
EOF
}

target="${1:-wrangler}"
case "$target" in
  -h|--help)
    usage
    exit 0
    ;;
  wrangler)
    ;;
  *)
    echo "Unknown target: $target. This installer only provides native Wrangler." >&2
    usage >&2
    exit 2
    ;;
esac

if [[ "${PREFIX:-}" != "/data/data/com.termux/files/usr" ]]; then
  echo "This installer only supports the standard native Termux prefix:" >&2
  echo "  /data/data/com.termux/files/usr" >&2
  exit 1
fi

arch=$(dpkg --print-architecture 2>/dev/null || true)
if [[ "$arch" != "aarch64" ]]; then
  echo "Only Termux aarch64 is currently supported; detected: ${arch:-unknown}" >&2
  exit 1
fi

workdir=$(mktemp -d "${TMPDIR:-$PREFIX/tmp}/termux-wrangler.XXXXXX")
trap 'rm -rf "$workdir"' EXIT
index="$workdir/release-index.tsv"
curl -fL --retry 4 --retry-all-errors -o "$index" "$INDEX_URL"

lookup() {
  local kind=$1
  local minor=$2
  awk -F '\t' -v wanted_kind="$kind" -v wanted_minor="$minor" '
    NR > 1 && $1 == wanted_kind && $2 == wanted_minor { print; exit }
  ' "$index"
}

download_row() {
  local row=$1
  local row_kind row_minor version architecture filename checksum url
  IFS=$'\t' read -r row_kind row_minor version architecture filename checksum url <<< "$row"
  local destination="$workdir/$filename"
  curl -fL --retry 4 --retry-all-errors -o "$destination" "$url"
  printf '%s  %s\n' "$checksum" "$destination" | sha256sum -c - >&2
  printf '%s\n' "$destination"
}

row=$(lookup "wrangler" "-")
if [[ -z "$row" ]]; then
  echo "No wrangler build exists in the latest release index." >&2
  exit 1
fi

file=$(download_row "$row")
apt-get update
apt-get install -y --allow-downgrades --no-install-recommends "$file"
echo "Installed Wrangler for $arch"
wrangler --version

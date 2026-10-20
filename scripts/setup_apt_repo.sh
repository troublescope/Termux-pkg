#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail

REPO_URL="${ADYBAG_TERMUX_REPO_URL:-http://144.21.61.111/termux}"
EXPECTED_FINGERPRINT="2E44CCEEA39C350159D5A77F8C9A482AAD291541"
KEY_URL="https://raw.githubusercontent.com/troublescope/Termux-pkg/main/apt/repo-signing-key.asc"
PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"
KEYRING_DIR="$PREFIX/etc/apt/keyrings"
KEYRING="$KEYRING_DIR/adybag-termux.gpg"
SOURCE="$PREFIX/etc/apt/sources.list.d/adybag-termux.list"

echo "Installing signed AdyBag native Termux repository..."
needed=()
command -v curl >/dev/null 2>&1 || needed+=(curl)
command -v gpg >/dev/null 2>&1 || needed+=(gnupg)
if ((${#needed[@]} > 0)); then
  pkg install -y "${needed[@]}" >/dev/null
fi
mkdir -p "$KEYRING_DIR" "$(dirname "$SOURCE")"
tmp="$(mktemp "${TMPDIR:-$PREFIX/tmp}/adybag-repo-key.XXXXXX")"
trap 'rm -f "$tmp" "$tmp.gpg"' EXIT
curl -fL --retry 3 --retry-all-errors "$KEY_URL" -o "$tmp"
actual="$(gpg --batch --with-colons --show-keys "$tmp" | awk -F: '$1=="fpr" {print $10; exit}')"
if [ "$actual" != "$EXPECTED_FINGERPRINT" ]; then
  echo "Repository signing-key fingerprint mismatch: $actual" >&2
  exit 1
fi
gpg --batch --yes --dearmor --output "$tmp.gpg" "$tmp"
install -m 0644 "$tmp.gpg" "$KEYRING"
printf 'deb [signed-by=%s] %s stable main\n' "$KEYRING" "$REPO_URL" > "$SOURCE"
apt -o Acquire::Retries=5 -o Acquire::http::Timeout=30 update
cat <<EOF
Repository enabled and signature verified.
Signing fingerprint: $EXPECTED_FINGERPRINT

Examples:
  pkg install wrangler
EOF

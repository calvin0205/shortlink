#!/usr/bin/env bash
# Generate locally-trusted TLS certificates for local HTTPS development.
# Uses mkcert — installs a local CA into the OS/browser trust stores so
# you get a green padlock without any browser warning.
#
# Run once after cloning:
#   bash scripts/gen-dev-certs.sh

set -euo pipefail

CERT_DIR="backend/certs"

# ── Check mkcert is installed ─────────────────────────────────────────────────
if ! command -v mkcert &>/dev/null; then
  echo "mkcert is not installed. Install it first:"
  echo ""
  echo "  Windows (winget):  winget install FiloSottile.mkcert"
  echo "  macOS (brew):      brew install mkcert"
  echo "  Linux:             https://github.com/FiloSottile/mkcert#linux"
  echo ""
  exit 1
fi

# ── Install the local CA into system/browser trust stores ────────────────────
echo "→ Installing local CA (may ask for sudo/admin password)…"
mkcert -install

# ── Generate certificate for localhost ───────────────────────────────────────
mkdir -p "$CERT_DIR"
mkcert \
  -key-file  "$CERT_DIR/key.pem" \
  -cert-file "$CERT_DIR/cert.pem" \
  localhost 127.0.0.1 ::1

echo ""
echo "✓ Certificates written to $CERT_DIR/"
echo ""
echo "Start the dev server with HTTPS:"
echo "  cd backend"
echo "  uvicorn app.main:app --reload --ssl-keyfile certs/key.pem --ssl-certfile certs/cert.pem"
echo ""
echo "Then open: https://localhost:8000/api/docs"

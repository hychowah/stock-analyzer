#!/usr/bin/env bash
# Agent-legible boot for analysis UI
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
export ARCHIVE_ROOT="${ARCHIVE_ROOT:-$ROOT/archive}"
echo "ARCHIVE_ROOT=$ARCHIVE_ROOT"
exec python3 -m apps.analysis_web --host 127.0.0.1 --port "${PORT:-8765}"

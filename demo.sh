#!/usr/bin/env bash
# Seed a fictional NAS and convene the board for the three Round 1 scenarios.
# The library only appends. This script stages a fresh ledger so the showcase
# is exactly these three receipts.

set -euo pipefail

cd "$(dirname "$0")"

if command -v python3 >/dev/null 2>&1; then
  PY=python3
else
  PY=python
fi

"$PY" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' \
  || { echo "Python 3.10 or newer is required." >&2; exit 1; }

NAS="${BOARDROOM_NAS:-demo-nas}"
LEDGER="${BOARDROOM_LEDGER:-ledger/DECISIONS.md}"
TODAY="${BOARDROOM_TODAY:-2026-10-26}"
export PYTHONUNBUFFERED=1

echo "THE NAS BOARDROOM"
echo "Seeding a fictional volume at ${NAS}"
echo "Calendar pinned to ${TODAY} so last quarter stays Q3 2026."
echo "Speeches use a local Ollama model only when one is already listening on 127.0.0.1."
echo

"$PY" -m boardroom.seed --nas "$NAS" --reset-ledger "$LEDGER"

run() {
  local title="$1"
  local request="$2"
  echo
  echo "========================================================================"
  echo "SCENARIO  ${title}"
  echo "========================================================================"
  echo
  "$PY" -m boardroom --nas "$NAS" --ledger "$LEDGER" --today "$TODAY" "$request"
}

run "a. Duplicate-cleanup proposal" "find duplicate photos and propose cleanup"
run "b. What did I sign last quarter?" "what did I sign last quarter?"
run "c. Risky delete the Auditor blocks" "delete all files in Documents/Contracts, including the signed originals"

echo
echo "Three sessions are on the record in ${LEDGER}:"
grep '^## BRD-' "$LEDGER"

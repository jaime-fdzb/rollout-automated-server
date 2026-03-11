#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_URL="http://localhost:8000"

usage() {
  cat <<EOF
Usage: $(basename "$0") <command> [options]

Commands:
  sheet-data          Fetch sheet data and save it as Markdown
    --sheet NAME      Sheet tab name         (default: migration_planer)
    --range RANGE     A1-notation range      (default: A1:Q1201)

  batch               Mark a list of tenants with a given status in Google Sheets
    --tenants-file F  File with one tenant per line
                      (default: ai/data/next_batch_tenants.txt)
    --status STATUS   Status to assign       (default: migrating)

  help                Show this help message

Examples:
  $(basename "$0") sheet-data
  $(basename "$0") sheet-data --sheet migration_planer --range A1:D500

  $(basename "$0") batch
  $(basename "$0") batch --tenants-file ai/data/next_batch_tenants.txt --status migrating
EOF
}

STARTED_APP=false

ensure_running() {
  local status
  status=$(docker compose -f "$SCRIPT_DIR/docker-compose.yaml" ps --status running --services 2>/dev/null)
  if ! echo "$status" | grep -q "^app$"; then
    echo "Server is not running — starting it now..."
    docker compose -f "$SCRIPT_DIR/docker-compose.yaml" up -d --no-deps app
    STARTED_APP=true
    echo -n "Waiting for server to be ready"
    for i in $(seq 1 20); do
      if curl -sf "http://localhost:8000/" >/dev/null 2>&1; then
        echo " ready."
        return
      fi
      echo -n "."
      sleep 1
    done
    echo ""
    echo "Error: server did not become ready in time." >&2
    exit 1
  fi
}

teardown() {
  if [[ "$STARTED_APP" == true ]]; then
    echo "Stopping server..."
    docker compose -f "$SCRIPT_DIR/docker-compose.yaml" stop app
  fi
}

cmd_sheet_data() {
  local sheet="migration_planer"
  local range="A1:Q1201"

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --sheet) sheet="$2"; shift 2 ;;
      --range) range="$2"; shift 2 ;;
      *) echo "Unknown option: $1"; usage; exit 1 ;;
    esac
  done

  trap teardown EXIT

  ensure_running

  echo "Fetching sheet '${sheet}' range '${range}'..."

  response=$(curl -sf "${BASE_URL}/sheet-data?sheet=${sheet}&range=${range}")

  row_count=$(echo "$response" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['row_count'])" 2>/dev/null || echo "?")
  saved_to=$(echo "$response" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['saved_to'])" 2>/dev/null || echo "?")

  echo "Done — ${row_count} rows saved to ${saved_to}"
}

cmd_batch() {
  local tenants_file="$SCRIPT_DIR/ai/data/next_batch_tenants.txt"
  local status="migrating"

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --tenants-file) tenants_file="$2"; shift 2 ;;
      --status)       status="$2";       shift 2 ;;
      *) echo "Unknown option: $1"; usage; exit 1 ;;
    esac
  done

  if [[ ! -f "$tenants_file" ]]; then
    echo "Error: tenants file not found: $tenants_file" >&2
    exit 1
  fi

  # Build JSON payload from the tenants file
  payload=$(python3 - "$tenants_file" "$status" <<'PYEOF'
import json, sys
tenants_file, status = sys.argv[1], sys.argv[2]
tenants = [l.strip() for l in open(tenants_file) if l.strip()]
print(json.dumps({"tenants": tenants, "status": status}))
PYEOF
)

  tenant_count=$(python3 -c "import json,sys; print(len(json.loads(sys.argv[1])['tenants']))" "$payload")

  trap teardown EXIT

  ensure_running

  echo "Marking ${tenant_count} tenants as '${status}'..."

  response=$(curl -sf -X POST \
    -H "Content-Type: application/json" \
    -d "$payload" \
    "${BASE_URL}/batch")

  queued=$(echo "$response" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['queued'])" 2>/dev/null || echo "?")
  echo "Done — ${queued} tenants marked as '${status}'."
}

# ── Main ──────────────────────────────────────────────────────────────────────
if [[ $# -eq 0 ]]; then
  usage; exit 1
fi

case "$1" in
  sheet-data) shift; cmd_sheet_data "$@" ;;
  batch)      shift; cmd_batch      "$@" ;;
  help|--help|-h) usage ;;
  *) echo "Unknown command: $1"; usage; exit 1 ;;
esac

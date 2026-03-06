#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_URL="http://localhost:8000"

usage() {
  cat <<EOF
Usage: $(basename "$0") <command> [options]

Commands:
  sheet-data          Fetch sheet data and save it as Markdown
    --sheet NAME      Sheet tab name         (default: mexico_migration_status)
    --range RANGE     A1-notation range      (default: A1:C1000)

  help                Show this help message

Examples:
  $(basename "$0") sheet-data
  $(basename "$0") sheet-data --sheet mexico_migration_status --range A1:D500
EOF
}

STARTED_APP=false

ensure_running() {
  local status
  status=$(docker compose -f "$SCRIPT_DIR/docker-compose.yaml" ps --status running --services 2>/dev/null)
  if ! echo "$status" | grep -q "^app$"; then
    echo "Server is not running — starting it now..."
    # Start only the app service; the watcher is not needed for data fetching
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
  local sheet="mexico_migration_status"
  local range="A1:C1000"

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

  response=$(curl -sf "http://localhost:8000/sheet-data?sheet=${sheet}&range=${range}")

  row_count=$(echo "$response" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['row_count'])" 2>/dev/null || echo "?")
  saved_to=$(echo "$response" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['saved_to'])" 2>/dev/null || echo "?")

  # Map container path /data/... to host path ./data/...
  host_path="${saved_to/#\/data/$SCRIPT_DIR\/data}"

  echo "Done — ${row_count} rows"
  echo "Container path : ${saved_to}"
  echo "Host path      : ${host_path}"
}

# ── Main ──────────────────────────────────────────────────────────────────────
if [[ $# -eq 0 ]]; then
  usage; exit 1
fi

case "$1" in
  sheet-data) shift; cmd_sheet_data "$@" ;;
  help|--help|-h) usage ;;
  *) echo "Unknown command: $1"; usage; exit 1 ;;
esac

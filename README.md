# Rollout Automated Server

Monitors a Gmail inbox for tenant migration completion emails, records each result, and syncs it to a Google Sheet. Built with two containerised services that communicate over an internal HTTP webhook.

---

## Architecture

```text
Gmail INBOX
    │
    │  IMAP IDLE
    ▼
imap_watcher.py  ──── POST /webhook ────▶  server.py
                                               │         │
                                           SQLite DB   Google Sheets
```

---

## Services

### `imap_watcher.py`

Connects to Gmail over IMAP and uses the **IDLE** command to receive real-time push notifications when a new email arrives. For each new message it:

1. Downloads and parses the email body looking for the pattern `Tenant Tenant <name> terminó su ejecución <result>`.
2. Extracts the tenant name and determines the status (`success` / `error`).
3. Posts the result as JSON to the internal webhook (`POST /webhook`).

If the connection drops it automatically reconnects after 10 seconds.

### `server.py`

A FastAPI HTTP server that exposes three endpoints:

| Endpoint | Description |
|---|---|
| `POST /webhook` | Receives a `{ tenant, status }` event, persists it to SQLite, and syncs it to Google Sheets. |
| `GET /` | Renders an HTML dashboard showing the 50 most recent execution results. Includes a **Generate Data** button that triggers a sheet fetch. |
| `GET /sheet-data?sheet=<name>&range=<A1>` | Fetches the given range from Google Sheets via Apps Script, saves it as a Markdown file to `SHEET_DATA_DIR`, and returns the rows as JSON. |

Google Sheets sync is done via a Google Apps Script web app (`sheet_script.gs`). The script must be deployed with **"Anyone"** access for the requests to be accepted.

---

## Running

Copy `.env.example` to `.env`, fill in the values (see below), then run:

```bash
docker compose up --build
```

The dashboard will be available at [http://localhost:8000](http://localhost:8000).

---

## CLI — `rollout.sh`

A helper script for common operations from your local machine. It starts the `app` container automatically if it is not already running, and stops it again once the command finishes (only if it was started by the script).

### Commands

#### `sheet-data`

Fetches a sheet range from Google Sheets and saves it as a Markdown file to `./data/sheet_data/`.

```bash
# With defaults (sheet: migration_planer, range: A1:Q1201)
./rollout.sh sheet-data

# Override sheet or range
./rollout.sh sheet-data --sheet migration_planer --range A1:D500
```

Example output:

```
Server is not running — starting it now...
Waiting for server to be ready........ ready.
Fetching sheet 'migration_planer' range 'A1:Q1201'...
Done — 42 rows
Container path : /data/sheet_data/migration_planer.md
Host path      : /home/user/rollout-automated-server/data/sheet_data/migration_planer.md
Stopping server...
```

The generated Markdown file has a metadata header followed by a table and is designed to be easy to read by an AI agent.

---

## Environment variables (`.env`)

```env
# IMAP credentials — use a Gmail App Password, not your account password.
# Generate one at: https://myaccount.google.com/apppasswords
IMAP_SERVER=imap.gmail.com
EMAIL_ACCOUNT=example@email.com
EMAIL_PASSWORD=xxxx xxxx xxxx xxxx

# Internal URL of the webhook server. Must match the service name in docker-compose.
WEBHOOK_URL=http://app:8000/webhook

# Google Apps Script web app URL.
# Deploy the script with "Execute as: Me" and "Who has access: Anyone".
GOOGLE_SCRIPT_URL=https://script.google.com/macros/s/<deployment-id>/exec

# Path to the SQLite database file inside the container.
# Mapped to ./data on the host via the docker-compose volume.
DB_PATH=/data/events.db

# Directory where fetched sheet data is saved as Markdown files inside the container.
# Mapped to ./data on the host via the docker-compose volume.
SHEET_DATA_DIR=/data/sheet_data

# (Unused by current code — reserved for future polling interval control)
CHECK_INTERVAL=60
```

import logging
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

GOOGLE_SCRIPT_URL = os.getenv("GOOGLE_SCRIPT_URL")
SHEET_DATA_DIR = Path(os.getenv("SHEET_DATA_DIR", "sheet_data"))


class Event(BaseModel):
    tenant: str
    status: str


class BatchEvent(BaseModel):
    tenants: list[str]
    status: str = "migrando"


def send_to_sheet(data: dict) -> None:
    if not GOOGLE_SCRIPT_URL:
        logger.warning("GOOGLE_SCRIPT_URL is not set, skipping sheet sync")
        return

    try:
        response = requests.post(GOOGLE_SCRIPT_URL, json=data, timeout=5, allow_redirects=True)
        response.raise_for_status()
        logger.info(f"Sheet sync OK → {data}")
    except requests.HTTPError as e:
        logger.error(f"Sheet sync failed with HTTP error: {e}")
    except requests.RequestException as e:
        logger.error(f"Sheet sync failed: {e}")


def send_batch_to_sheet(rows: list[dict]) -> None:
    """Send multiple rows to the sheet in a single Apps Script call."""
    if not GOOGLE_SCRIPT_URL:
        logger.warning("GOOGLE_SCRIPT_URL is not set, skipping batch sheet sync")
        return

    try:
        response = requests.post(GOOGLE_SCRIPT_URL, json=rows, timeout=30, allow_redirects=True)
        response.raise_for_status()
        logger.info(f"Batch sheet sync OK → {len(rows)} rows")
    except requests.HTTPError as e:
        logger.error(f"Batch sheet sync failed with HTTP error: {e}")
    except requests.RequestException as e:
        logger.error(f"Batch sheet sync failed: {e}")


@app.post("/webhook")
def receive_event(event: Event):
    now = datetime.now(ZoneInfo("America/Santiago")).isoformat()
    send_to_sheet({"tenant": event.tenant, "status": event.status, "timestamp": now})
    return {"stored": True}


@app.post("/batch")
def receive_batch(batch: BatchEvent):
    """Mark multiple tenants with the same status in a single sheet call.

    Typical use: flag the next migration batch as 'migrando' right after the
    PR is created, before execution starts.

    Body: {"tenants": ["tenant1", "tenant2", ...], "status": "migrando"}
    """
    if not batch.tenants:
        raise HTTPException(status_code=422, detail="tenants list must not be empty")

    now = datetime.now(ZoneInfo("America/Santiago")).isoformat()
    rows = [{"tenant": t, "status": batch.status, "timestamp": now} for t in batch.tenants]
    send_batch_to_sheet(rows)

    logger.info(f"Batch received: {len(rows)} tenants with status='{batch.status}'")
    return {"queued": len(rows), "status": batch.status, "timestamp": now}


@app.get("/", response_class=HTMLResponse)
def dashboard():
    html = """
    <h1>Email Migration Monitor</h1>
    <button
        onclick="
            this.disabled = true;
            this.textContent = 'Fetching…';
            fetch('/sheet-data?sheet=migration_planer&range=A1:Q1201')
                .then(r => r.json())
                .then(d => {
                    this.textContent = 'Generate Data';
                    this.disabled = false;
                    alert('Done! ' + d.row_count + ' rows saved to ' + d.saved_to);
                })
                .catch(err => {
                    this.textContent = 'Generate Data';
                    this.disabled = false;
                    alert('Error: ' + err);
                });
        "
        style="margin-bottom:16px;padding:8px 16px;cursor:pointer;"
    >Generate Data</button>
    <p style="color:#555;">Migration events are recorded directly in Google Sheets. Use the button above to refresh local sheet data.</p>
    """
    return html


def _rows_to_markdown(rows: list[dict], sheet: str, range_: str, fetched_at: str) -> str:
    """Render a list of row-dicts as a Markdown table with a metadata header."""
    lines = [
        f"# Sheet data: {sheet}",
        f"- **Range:** {range_}",
        f"- **Fetched at:** {fetched_at}",
        f"- **Row count:** {len(rows)}",
        "",
    ]

    if not rows:
        lines.append("_No data returned._")
        return "\n".join(lines)

    headers = list(rows[0].keys())
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join("---" for _ in headers) + " |")

    for row in rows:
        cells = [str(row.get(h, "")).replace("|", "\\|") for h in headers]
        lines.append("| " + " | ".join(cells) + " |")

    return "\n".join(lines)


@app.get("/sheet-data")
def fetch_sheet_data(
    sheet: str = Query(..., description="Sheet tab name"),
    range: str = Query(..., description="A1-notation range, e.g. A1:E100"),
):
    """Fetch a range from Google Sheets via Apps Script and persist it as Markdown."""
    if not GOOGLE_SCRIPT_URL:
        raise HTTPException(status_code=503, detail="GOOGLE_SCRIPT_URL is not configured")

    try:
        response = requests.get(
            GOOGLE_SCRIPT_URL,
            params={"sheet": sheet, "range": range},
            timeout=10,
            allow_redirects=True,
        )
        response.raise_for_status()
    except requests.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Apps Script HTTP error: {e}") from e
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Request failed: {e}") from e

    try:
        rows: list[dict] = response.json()
    except ValueError as e:
        logger.error(f"Apps Script non-JSON response (status {response.status_code}): {response.text[:500]}")
        raise HTTPException(
            status_code=502,
            detail=f"Apps Script did not return JSON. Status: {response.status_code}. Body: {response.text[:300]}",
        ) from e

    fetched_at = datetime.now(ZoneInfo("America/Santiago")).isoformat()

    SHEET_DATA_DIR.mkdir(exist_ok=True)
    safe_sheet = "".join(c if c.isalnum() or c in "-_" else "_" for c in sheet)
    output_path = SHEET_DATA_DIR / f"{safe_sheet}.md"
    output_path.write_text(_rows_to_markdown(rows, sheet, range, fetched_at), encoding="utf-8")

    logger.info(f"Sheet data saved → {output_path} ({len(rows)} rows)")

    return {
        "sheet": sheet,
        "range": range,
        "fetched_at": fetched_at,
        "row_count": len(rows),
        "saved_to": str(output_path),
        "rows": rows,
    }

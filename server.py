import logging
import os
import sqlite3
from datetime import datetime

import requests
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

DB = os.getenv("DB_PATH", "events.db")
GOOGLE_SCRIPT_URL = os.getenv("GOOGLE_SCRIPT_URL")


def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS executions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant TEXT,
        status TEXT,
        created_at TEXT
    )
    """)

    conn.commit()
    conn.close()


init_db()


class Event(BaseModel):
    tenant: str
    status: str

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


@app.post("/webhook")
def receive_event(event: Event):

    now = datetime.utcnow().isoformat()

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute(
        "INSERT INTO executions (tenant, status, created_at) VALUES (?, ?, ?)",
        (event.tenant, event.status, now)
    )

    conn.commit()
    conn.close()

    send_to_sheet({"tenant": event.tenant, "status": event.status, "timestamp": now})

    return {"stored": True}


@app.get("/", response_class=HTMLResponse)
def dashboard():

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    rows = c.execute("""
        SELECT tenant,status,created_at
        FROM executions
        ORDER BY created_at DESC
        LIMIT 50
    """).fetchall()

    conn.close()

    html = "<h1>Email Migration Monitor</h1><table border=1>"
    html += "<tr><th>Tenant</th><th>Status</th><th>Time</th></tr>"

    for tenant, status, time in rows:

        color = "green" if status == "success" else "red"

        html += f"""
        <tr>
            <td>{tenant}</td>
            <td style="color:{color}">{status}</td>
            <td>{time}</td>
        </tr>
        """

    html += "</table>"

    return html

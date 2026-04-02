import json
import os
import time
import re
import requests
from imapclient import IMAPClient
import email
from email.header import decode_header as _decode_header

IMAP_SERVER = os.getenv("IMAP_SERVER")
EMAIL_ACCOUNT = os.getenv("EMAIL_ACCOUNT")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
WEBHOOK = os.getenv("WEBHOOK_URL")

# Derived from WEBHOOK_URL: http://app:8000/webhook → http://app:8000/batch
BATCH_URL = WEBHOOK.rsplit("/", 1)[0] + "/batch" if WEBHOOK else None

CHECK_FOLDER = "INBOX"

# Regular migration completion email
body_pattern = r"Tenant Tenant (\S+) terminó su ejecución (.*)"
subject_pattern = r"Descuadres en el saldo de vacaciones"

# Vacation unbalances summary email (has a JSON attachment with inactive tenants)
unbalances_body_pattern = r"Tenant \[MX\] Migrar vacaciones mx grupo"

STATUS_KEYWORDS = [
    ("forced", "forzadamente"),
    ("failed", "errores"),
    ("success", "exitosamente"),
    ("skipped", "saltado"),
    ("done", "ya migrado"),
]


def resolve_status(text: str) -> str:
    for status, keyword in STATUS_KEYWORDS:
        if keyword in text:
            return status
    return "unknown"


last_uid = None


def log(msg):
    print(f"[MAIL WATCHER] {msg}", flush=True)


def decode_subject(raw):
    parts = _decode_header(raw)
    decoded = []
    for chunk, charset in parts:
        if isinstance(chunk, bytes):
            decoded.append(chunk.decode(charset or "utf-8", errors="ignore"))
        else:
            decoded.append(chunk)
    return "".join(decoded)


def parse_email(subject, body):

    # Primary: match on body
    m = re.search(body_pattern, body)

    if m:
        return {"tenant": m.group(1), "status": resolve_status(m.group(2))}

    # Fallback: detect via subject, extract tenant from body with a looser search
    decoded_subject = decode_subject(subject)
    if re.search(subject_pattern, decoded_subject):
        tenant_match = re.search(r"Tenant\s+(\S+)\s+terminó", body)
        if tenant_match:
            return {"tenant": tenant_match.group(1), "status": resolve_status(body)}

    return None


def send_webhook(data):
    try:
        r = requests.post(WEBHOOK, json=data, timeout=5)
        log(f"Webhook sent → {data} status={r.status_code}")
    except Exception as e:
        log(f"Webhook error: {e}")


def send_batch_webhook(tenants: list, status: str):
    if not BATCH_URL:
        log("WEBHOOK_URL not set, skipping batch")
        return
    try:
        r = requests.post(BATCH_URL, json={"tenants": tenants, "status": status}, timeout=30)
        log(f"Batch webhook sent → {len(tenants)} tenants as '{status}' status={r.status_code}")
    except Exception as e:
        log(f"Batch webhook error: {e}")


def process_new_messages(server):

    global last_uid

    all_uids = server.search(["ALL"])
    uids = [uid for uid in all_uids if last_uid is None or uid > last_uid]

    if not uids:
        log("No new messages")
        return

    log(f"Found {len(uids)} new message(s): UIDs {uids}")

    for uid, message_data in server.fetch(uids, ["RFC822"]).items():

        msg = email.message_from_bytes(message_data[b"RFC822"])

        subject = msg.get("Subject", "(no subject)")
        sender = msg.get("From", "(unknown)")
        log(f"📧 Processing email UID={uid} from={sender!r} subject={subject!r}")

        body = ""
        json_attachment = None

        if msg.is_multipart():
            for part in msg.walk():
                ct = part.get_content_type()
                filename = part.get_filename() or ""

                if ct == "text/plain":
                    charset = part.get_content_charset() or "utf-8"
                    body = part.get_payload(decode=True).decode(charset, errors="ignore")

                elif filename.endswith(".json"):
                    raw = part.get_payload(decode=True)
                    if raw:
                        try:
                            json_attachment = json.loads(raw.decode("utf-8", errors="ignore"))
                            log(f"JSON attachment found: {filename!r} ({len(json_attachment)} entries)")
                        except json.JSONDecodeError:
                            log(f"Failed to parse JSON attachment: {filename!r}")
        else:
            charset = msg.get_content_charset() or "utf-8"
            body = msg.get_payload(decode=True).decode(charset, errors="ignore")

        # Vacation unbalances summary: JSON attachment + matching body pattern
        if json_attachment is not None and re.search(unbalances_body_pattern, body):
            tenants = list(json_attachment.keys())
            log(f"Vacation unbalances email — marking {len(tenants)} tenants as 'no encontrado'")
            send_batch_webhook(tenants, "not_found")

        else:
            parsed = parse_email(subject, body)
            if parsed:
                log(f"Parsed event → {parsed}")
                send_webhook(parsed)
            else:
                log(f"Email did not match pattern, skipping webhook")

        last_uid = uid


def idle_loop():

    global last_uid

    while True:

        try:

            log("Connecting to IMAP server...")

            with IMAPClient(IMAP_SERVER) as server:

                server.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)

                log("✅ Connected to IMAP server")

                server.select_folder(CHECK_FOLDER)

                log(f"Watching folder: {CHECK_FOLDER}")

                uids = server.search(["ALL"])

                if uids:
                    last_uid = uids[-1]
                    log(f"Initialized last UID: {last_uid}")

                while True:

                    log("Entering IDLE mode")

                    server.idle()

                    responses = server.idle_check(timeout=300)

                    server.idle_done()

                    log(f"IDLE woke up — responses: {responses}")

                    process_new_messages(server)

        except Exception as e:

            log(f"⚠️ IMAP connection lost: {e}")
            log("Reconnecting in 10 seconds...")

            time.sleep(10)


if __name__ == "__main__":

    log("Starting IMAP watcher")

    idle_loop()

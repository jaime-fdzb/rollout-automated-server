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

CHECK_FOLDER = "INBOX"

body_pattern = r"Tenant Tenant (\S+) terminó su ejecución (.*)"
subject_pattern = r"Descuadres en el saldo de vacaciones"

STATUS_KEYWORDS = [
    ("forced", "forzadamente"),
    ("failed", "errores"),
    ("success", "exitosamente"),
    ("skipped", "saltado"),
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


def process_new_messages(server):

    global last_uid

    # Fetch all UIDs (integers only — fast, no email content downloaded)
    # and filter in Python. Avoids Gmail's UID X:* range quirk where
    # searching "UID 7921:*" with no new messages returns the last
    # existing UID instead of an empty result.
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

        if msg.is_multipart():

            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    charset = part.get_content_charset() or "utf-8"
                    body = part.get_payload(decode=True).decode(charset, errors="ignore")

        else:
            charset = msg.get_content_charset() or "utf-8"
            body = msg.get_payload(decode=True).decode(charset, errors="ignore")

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

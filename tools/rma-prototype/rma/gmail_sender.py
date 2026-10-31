"""Send email via GAPP Gmail OAuth (same credential as n8n)."""

from __future__ import annotations

import base64
import json
import subprocess
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

N8N_CONTAINER = "n8n.1.kf6steeqlrxu00qmbp2wwfv7z"
GMAIL_CRED_ID = "gmailHermesOAuth20260612"


def _load_n8n_gmail_credential() -> dict[str, Any]:
    raw = subprocess.check_output(
        [
            "docker",
            "exec",
            N8N_CONTAINER,
            "n8n",
            "export:credentials",
            f"--id={GMAIL_CRED_ID}",
            "--decrypted",
        ],
        stderr=subprocess.STDOUT,
        text=True,
        timeout=60,
    )
    rows = json.loads(raw)
    if not rows:
        raise RuntimeError("GAPP Gmail OAuth credential not found in n8n")
    return rows[0]["data"]


def _build_credentials(data: dict[str, Any]) -> Credentials:
    oauth = data.get("oauthTokenData") or {}
    creds = Credentials(
        token=oauth.get("access_token"),
        refresh_token=oauth.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=data.get("clientId"),
        client_secret=data.get("clientSecret"),
        scopes=(data.get("scope") or "").split(),
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds


def send_gmail(
    *,
    to_addrs: list[str],
    subject: str,
    body: str,
    from_addr: str | None = None,
    thread_id_header: str | None = None,
    gmail_thread_id: str | None = None,
) -> str | None:
    """Send via Gmail API. Returns Gmail threadId if available."""
    if not to_addrs:
        return None

    data = _load_n8n_gmail_credential()
    creds = _build_credentials(data)
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)

    sender = from_addr
    if not sender:
        profile = service.users().getProfile(userId="me").execute()
        sender = profile.get("emailAddress")

    msg = MIMEMultipart("alternative")
    msg["From"] = sender
    msg["To"] = ", ".join(to_addrs)
    msg["Subject"] = subject
    if thread_id_header:
        msg["Message-ID"] = f"<{thread_id_header}>"
        msg["References"] = f"<{thread_id_header}>"
        msg["In-Reply-To"] = f"<{thread_id_header}>"
    msg.attach(MIMEText(body, "plain", "utf-8"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
    payload: dict[str, Any] = {"raw": raw}
    if gmail_thread_id:
        payload["threadId"] = gmail_thread_id

    sent = service.users().messages().send(userId="me", body=payload).execute()
    return sent.get("threadId")

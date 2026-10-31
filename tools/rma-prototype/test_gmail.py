#!/usr/bin/env python3
"""Verify Gmail OAuth loads from n8n (does not send email)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from rma.gmail_sender import _build_credentials, _load_n8n_gmail_credential
from googleapiclient.discovery import build

data = _load_n8n_gmail_credential()
creds = _build_credentials(data)
service = build("gmail", "v1", credentials=creds, cache_discovery=False)
profile = service.users().getProfile(userId="me").execute()
print("Gmail OK")
print("mailbox:", profile.get("emailAddress"))
print("scopes:", data.get("scope"))

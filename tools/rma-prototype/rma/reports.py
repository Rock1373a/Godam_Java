"""CSV report export for RME records."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from rma.db import RmeDatabase

EXPORT_DIR = Path(__file__).resolve().parent.parent / "exports"

COLUMNS = [
    "id",
    "rme_number",
    "case_id",
    "partner_name",
    "part_number",
    "quantity",
    "serial_number",
    "rme_type",
    "status",
    "outbound_number",
    "replacement_serial_number",
    "created_at",
    "received_at",
    "outbound_at",
    "delivered_at",
    "email_subject",
    "notes",
]


def export_rme_report(db: RmeDatabase, *, status: str | None = None) -> Path:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = f"_{status}" if status else "_all"
    out = EXPORT_DIR / f"rme_report{suffix}_{stamp}.csv"
    rows = db.list_all(status=status)
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in COLUMNS})
    return out

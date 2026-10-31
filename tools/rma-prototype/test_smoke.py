#!/usr/bin/env python3
"""Non-interactive smoke test for RME prototype."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from rma.db import RmeDatabase
from rma.email_service import RmeEmailService, build_email_subject, build_thread_id
from rma.reports import export_rme_report

db = RmeDatabase("/tmp/rma_test.db")
mail = RmeEmailService()
draft = {
    "rme_number": "RME-TEST-001",
    "case_id": "CASE-99",
    "partner_name": "Huawei",
    "part_number": "PN-12345",
}
subj = build_email_subject(draft)
r = db.create_rme(
    rme_number="RME-TEST-001",
    case_id="CASE-99",
    partner_name="Huawei",
    part_number="PN-12345",
    quantity=1,
    serial_number="SN-ABC",
    rme_type="DOA",
    email_subject=subj,
    email_thread_id=build_thread_id("RME-TEST-001"),
)
mail.notify_created(r, db)
r2 = db.mark_received(r["id"], serial_number="SN-ABC")
mail.notify_received(r2, db)
r3 = db.set_outbound(r2["id"], outbound_number="OB-7788")
r4 = db.mark_delivered(
    r3["id"], replacement_serial_number="SN-REPL-999", outbound_number="OB-7788"
)
mail.notify_closed(r4, db)
path = export_rme_report(db)
print("OK", r4["status"], path)

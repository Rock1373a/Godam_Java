"""SQLite persistence for RME records."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_DB = Path(__file__).resolve().parent.parent / "data" / "rma.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS rme_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rme_number TEXT NOT NULL UNIQUE,
    case_id TEXT NOT NULL,
    partner_name TEXT NOT NULL,
    part_number TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    serial_number TEXT NOT NULL,
    rme_type TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'open',
    email_subject TEXT NOT NULL,
    email_thread_id TEXT,
    gmail_thread_id TEXT,
    outbound_number TEXT,
    replacement_serial_number TEXT,
    created_at TEXT NOT NULL,
    received_at TEXT,
    outbound_at TEXT,
    delivered_at TEXT,
    notes TEXT DEFAULT '',
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_rme_status ON rme_records(status);
CREATE INDEX IF NOT EXISTS idx_rme_case ON rme_records(case_id);
CREATE INDEX IF NOT EXISTS idx_rme_partner ON rme_records(partner_name);

CREATE TABLE IF NOT EXISTS rme_email_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rme_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    recipients TEXT NOT NULL,
    subject TEXT NOT NULL,
    body_preview TEXT,
    sent_at TEXT NOT NULL,
    dry_run INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (rme_id) REFERENCES rme_records(id)
);
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


class RmeDatabase:
    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = Path(db_path or DEFAULT_DB)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA)
            cols = {r[1] for r in conn.execute("PRAGMA table_info(rme_records)").fetchall()}
            if "gmail_thread_id" not in cols:
                conn.execute("ALTER TABLE rme_records ADD COLUMN gmail_thread_id TEXT")

    def set_gmail_thread_id(self, rme_id: int, gmail_thread_id: str) -> None:
        with self.transaction() as conn:
            conn.execute(
                "UPDATE rme_records SET gmail_thread_id = ?, updated_at = ? WHERE id = ?",
                (gmail_thread_id, utc_now(), rme_id),
            )

    @contextmanager
    def transaction(self):
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def create_rme(
        self,
        *,
        rme_number: str,
        case_id: str,
        partner_name: str,
        part_number: str,
        quantity: int,
        serial_number: str,
        rme_type: str,
        email_subject: str,
        email_thread_id: str,
        notes: str = "",
    ) -> dict[str, Any]:
        now = utc_now()
        with self.transaction() as conn:
            cur = conn.execute(
                """
                INSERT INTO rme_records (
                    rme_number, case_id, partner_name, part_number, quantity,
                    serial_number, rme_type, status, email_subject, email_thread_id,
                    created_at, updated_at, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'open', ?, ?, ?, ?, ?)
                """,
                (
                    rme_number.strip(),
                    case_id.strip(),
                    partner_name.strip(),
                    part_number.strip(),
                    int(quantity),
                    serial_number.strip(),
                    (rme_type or "").strip(),
                    email_subject,
                    email_thread_id,
                    now,
                    now,
                    notes.strip(),
                ),
            )
            row_id = cur.lastrowid
        return self.get_by_id(row_id)

    def get_by_id(self, rme_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM rme_records WHERE id = ?", (rme_id,)).fetchone()
        return dict(row) if row else None

    def get_by_rme_number(self, rme_number: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM rme_records WHERE rme_number = ? COLLATE NOCASE",
                (rme_number.strip(),),
            ).fetchone()
        return dict(row) if row else None

    def list_all(self, status: str | None = None) -> list[dict[str, Any]]:
        with self._connect() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM rme_records WHERE status = ? ORDER BY created_at DESC",
                    (status,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM rme_records ORDER BY created_at DESC"
                ).fetchall()
        return [dict(r) for r in rows]

    def mark_received(self, rme_id: int, *, serial_number: str) -> dict[str, Any]:
        record = self.get_by_id(rme_id)
        if not record:
            raise ValueError("RME not found")
        if record["status"] != "open":
            raise ValueError(f"Cannot receive RME in status '{record['status']}'")
        expected = (record["serial_number"] or "").strip().lower()
        actual = serial_number.strip()
        if expected and actual.lower() != expected:
            raise ValueError(
                f"Serial mismatch: expected '{record['serial_number']}', got '{actual}'"
            )
        now = utc_now()
        with self.transaction() as conn:
            conn.execute(
                """
                UPDATE rme_records
                SET status = 'received', received_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (now, now, rme_id),
            )
        return self.get_by_id(rme_id)

    def set_outbound(self, rme_id: int, *, outbound_number: str) -> dict[str, Any]:
        record = self.get_by_id(rme_id)
        if not record:
            raise ValueError("RME not found")
        if record["status"] not in ("received", "outbound_ready"):
            raise ValueError(f"Cannot set outbound for status '{record['status']}'")
        now = utc_now()
        with self.transaction() as conn:
            conn.execute(
                """
                UPDATE rme_records
                SET status = 'outbound_ready',
                    outbound_number = ?,
                    outbound_at = COALESCE(outbound_at, ?),
                    updated_at = ?
                WHERE id = ?
                """,
                (outbound_number.strip(), now, now, rme_id),
            )
        return self.get_by_id(rme_id)

    def mark_delivered(
        self,
        rme_id: int,
        *,
        replacement_serial_number: str,
        outbound_number: str | None = None,
    ) -> dict[str, Any]:
        record = self.get_by_id(rme_id)
        if not record:
            raise ValueError("RME not found")
        if record["status"] not in ("received", "outbound_ready"):
            raise ValueError(f"Cannot deliver RME in status '{record['status']}'")
        now = utc_now()
        ob = (outbound_number or record.get("outbound_number") or "").strip()
        if not ob:
            raise ValueError("Outbound number is required before delivery")
        repl = replacement_serial_number.strip()
        if not repl:
            raise ValueError("Replacement serial number is required")
        with self.transaction() as conn:
            conn.execute(
                """
                UPDATE rme_records
                SET status = 'closed',
                    replacement_serial_number = ?,
                    outbound_number = ?,
                    delivered_at = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (repl, ob, now, now, rme_id),
            )
        return self.get_by_id(rme_id)

    def log_email(
        self,
        *,
        rme_id: int,
        event_type: str,
        recipients: list[str],
        subject: str,
        body_preview: str,
        dry_run: bool,
    ) -> None:
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO rme_email_log (rme_id, event_type, recipients, subject, body_preview, sent_at, dry_run)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rme_id,
                    event_type,
                    ", ".join(recipients),
                    subject,
                    body_preview[:500],
                    utc_now(),
                    1 if dry_run else 0,
                ),
            )

    def email_logs_for_rme(self, rme_id: int) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM rme_email_log WHERE rme_id = ? ORDER BY sent_at ASC",
                (rme_id,),
            ).fetchall()
        return [dict(r) for r in rows]

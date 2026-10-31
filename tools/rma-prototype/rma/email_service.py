"""Email notifications for RME lifecycle (SMTP; dry-run for prototype)."""

from __future__ import annotations

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from dotenv import load_dotenv

load_dotenv()

try:
    from rma.gmail_sender import send_gmail
except ImportError:
    send_gmail = None


def _split_emails(value: str) -> list[str]:
    return [e.strip() for e in (value or "").split(",") if e.strip()]


def build_email_subject(rme: dict[str, Any]) -> str:
    return (
        f"[RME {rme['rme_number']}] Case {rme['case_id']} — "
        f"{rme['partner_name']} / {rme['part_number']}"
    )


def build_thread_id(rme_number: str) -> str:
    return f"rme-{rme_number.strip().lower()}@godam.local"


class RmeEmailService:
  """Uses same SMTP settings as GoDaam/Koda once configured in .env."""

  def __init__(self) -> None:
      self.backend = os.getenv("RMA_EMAIL_BACKEND", "gmail").strip().lower()
      self.from_addr = os.getenv("RMA_EMAIL_FROM", "")
      self.smtp_host = os.getenv("RMA_SMTP_HOST", "")
      self.smtp_port = int(os.getenv("RMA_SMTP_PORT", "587"))
      self.smtp_user = os.getenv("RMA_SMTP_USER", "")
      self.smtp_pass = os.getenv("RMA_SMTP_PASS", "")
      self.dry_run = os.getenv("RMA_EMAIL_DRY_RUN", "1").strip() not in ("0", "false", "False")

      self.mgmt_on_create = _split_emails(os.getenv("RMA_EMAIL_ON_CREATE_MGMT", ""))
      self.team_on_create = _split_emails(os.getenv("RMA_EMAIL_ON_CREATE_TEAM", ""))
      self.all_recipients = _split_emails(os.getenv("RMA_EMAIL_ALL", ""))

      if not self.all_recipients:
          self.all_recipients = sorted(set(self.mgmt_on_create + self.team_on_create))

  def _send(
      self,
      *,
      to_addrs: list[str],
      subject: str,
      body: str,
      thread_id: str | None,
      gmail_thread_id: str | None = None,
      rme_id: int | None = None,
      db=None,
  ) -> None:
      if not to_addrs:
          return

      if self.dry_run:
          print(f"[DRY-RUN EMAIL] To: {to_addrs}")
          print(f"  Subject: {subject}")
          print(f"  Backend: {self.backend}")
          print(f"  Body:\n{body}\n")
          return

      if self.backend == "gmail" and send_gmail is not None:
          new_thread = send_gmail(
              to_addrs=to_addrs,
              subject=subject,
              body=body,
              from_addr=self.from_addr or None,
              thread_id_header=thread_id,
              gmail_thread_id=gmail_thread_id,
          )
          if new_thread and rme_id and db and not gmail_thread_id:
              db.set_gmail_thread_id(rme_id, new_thread)
          return

      if not self.smtp_host:
          print(f"[EMAIL SKIPPED — no SMTP] To: {to_addrs} | {subject}")
          return

      msg = MIMEMultipart("alternative")
      msg["From"] = self.from_addr or "godam-rma@localhost"
      msg["To"] = ", ".join(to_addrs)
      msg["Subject"] = subject
      if thread_id:
          msg["Message-ID"] = f"<{thread_id}>"
          msg["References"] = f"<{thread_id}>"
          msg["In-Reply-To"] = f"<{thread_id}>"
      msg.attach(MIMEText(body, "plain", "utf-8"))

      with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as smtp:
          smtp.starttls()
          if self.smtp_user:
              smtp.login(self.smtp_user, self.smtp_pass)
          smtp.sendmail(msg["From"], to_addrs, msg.as_string())

  def notify_created(self, rme: dict[str, Any], db) -> None:
      subject = rme["email_subject"]
      thread_id = rme.get("email_thread_id") or build_thread_id(rme["rme_number"])
      body = (
          f"New RME created\n\n"
          f"RME Number: {rme['rme_number']}\n"
          f"Case ID: {rme['case_id']}\n"
          f"Partner: {rme['partner_name']}\n"
          f"Part Number: {rme['part_number']}\n"
          f"Quantity: {rme['quantity']}\n"
          f"Serial Number: {rme['serial_number']}\n"
          f"Status: OPEN\n"
          f"Created: {rme['created_at']}\n"
      )
      for group, addrs, event in (
          ("mgmt", self.mgmt_on_create, "created_mgmt"),
          ("team", self.team_on_create, "created_team"),
      ):
          if not addrs:
              continue
          self._send(
              to_addrs=addrs,
              subject=subject,
              body=body,
              thread_id=thread_id,
              gmail_thread_id=rme.get("gmail_thread_id"),
              rme_id=rme["id"],
              db=db,
          )
          db.log_email(
              rme_id=rme["id"],
              event_type=event,
              recipients=addrs,
              subject=subject,
              body_preview=body,
              dry_run=self.dry_run,
          )

  def notify_received(self, rme: dict[str, Any], db) -> None:
      subject = rme["email_subject"]
      thread_id = rme.get("email_thread_id")
      body = (
          f"RME received from vendor\n\n"
          f"RME Number: {rme['rme_number']}\n"
          f"Part: {rme['part_number']} | Serial: {rme['serial_number']}\n"
          f"Received at: {rme['received_at']}\n"
          f"Status: RECEIVED\n"
      )
      self._send(
          to_addrs=self.all_recipients,
          subject=subject,
          body=body,
          thread_id=thread_id,
          gmail_thread_id=rme.get("gmail_thread_id"),
          rme_id=rme["id"],
          db=db,
      )
      db.log_email(
          rme_id=rme["id"],
          event_type="received",
          recipients=self.all_recipients,
          subject=subject,
          body_preview=body,
          dry_run=self.dry_run,
      )

  def notify_closed(self, rme: dict[str, Any], db) -> None:
      subject = rme["email_subject"]
      thread_id = rme.get("email_thread_id")
      body = (
          f"RME closed — delivered\n\n"
          f"RME Number: {rme['rme_number']}\n"
          f"Outbound: {rme['outbound_number']}\n"
          f"Replacement Serial: {rme['replacement_serial_number']}\n"
          f"Original Serial: {rme['serial_number']}\n"
          f"Delivered at: {rme['delivered_at']}\n"
          f"Status: CLOSED\n"
      )
      self._send(
          to_addrs=self.all_recipients,
          subject=subject,
          body=body,
          thread_id=thread_id,
          gmail_thread_id=rme.get("gmail_thread_id"),
          rme_id=rme["id"],
          db=db,
      )
      db.log_email(
          rme_id=rme["id"],
          event_type="closed",
          recipients=self.all_recipients,
          subject=subject,
          body_preview=body,
          dry_run=self.dry_run,
      )

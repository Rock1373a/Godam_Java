#!/usr/bin/env python3
"""
GoDaam RMA (RME) Tracking — desktop TUI prototype.

Run: ./run.sh   or   python app.py

Not wired into production GoDaam yet — standalone for testing on VPS.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running without pip install -e .
sys.path.insert(0, str(Path(__file__).resolve().parent))

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table

from rma.db import RmeDatabase
from rma.email_service import RmeEmailService, build_email_subject, build_thread_id
from rma.reports import export_rme_report

console = Console()

STATUS_LABELS = {
    "open": "[yellow]OPEN[/]",
    "received": "[cyan]RECEIVED[/]",
    "outbound_ready": "[blue]OUTBOUND READY[/]",
    "closed": "[green]CLOSED[/]",
}


def show_header() -> None:
    console.print(
        Panel.fit(
            "[bold]GoDaam RMA / RME Tracker[/]\n[dim]Prototype — not deployed to production[/]",
            border_style="blue",
        )
    )


def status_badge(status: str) -> str:
    return STATUS_LABELS.get(status, status)


def print_rme_table(records: list[dict]) -> None:
    if not records:
        console.print("[dim]No RME records found.[/]")
        return
    table = Table(title="RME Records", box=box.ROUNDED, show_lines=True)
    table.add_column("ID", style="dim")
    table.add_column("RME #")
    table.add_column("Case ID")
    table.add_column("Partner")
    table.add_column("Part #")
    table.add_column("Qty", justify="right")
    table.add_column("Serial")
    table.add_column("Status")
    table.add_column("Outbound")
    for r in records:
        table.add_row(
            str(r["id"]),
            r["rme_number"],
            r["case_id"],
            r["partner_name"][:20],
            r["part_number"],
            str(r["quantity"]),
            (r["serial_number"] or "")[:18],
            status_badge(r["status"]),
            r.get("outbound_number") or "—",
        )
    console.print(table)


def print_rme_detail(r: dict, db: RmeDatabase) -> None:
    lines = [
        f"[bold]RME:[/] {r['rme_number']}  {status_badge(r['status'])}",
        f"[bold]Case ID:[/] {r['case_id']}",
        f"[bold]Partner:[/] {r['partner_name']}",
        f"[bold]Part:[/] {r['part_number']}  [bold]Qty:[/] {r['quantity']}",
        f"[bold]Serial:[/] {r['serial_number']}",
        f"[bold]RME Type:[/] {r.get('rme_type') or '—'}",
        f"[bold]Outbound:[/] {r.get('outbound_number') or '—'}",
        f"[bold]Replacement Serial:[/] {r.get('replacement_serial_number') or '—'}",
        f"[bold]Created:[/] {r['created_at']}",
        f"[bold]Received:[/] {r.get('received_at') or '—'}",
        f"[bold]Outbound at:[/] {r.get('outbound_at') or '—'}",
        f"[bold]Delivered:[/] {r.get('delivered_at') or '—'}",
        f"[bold]Email subject:[/] {r['email_subject']}",
    ]
    if r.get("notes"):
        lines.append(f"[bold]Notes:[/] {r['notes']}")
    console.print(Panel("\n".join(lines), title="RME Detail", border_style="cyan"))

    logs = db.email_logs_for_rme(r["id"])
    if logs:
        et = Table(title="Email log", box=box.SIMPLE)
        et.add_column("When")
        et.add_column("Event")
        et.add_column("To")
        et.add_column("Dry-run")
        for log in logs:
            et.add_row(
                log["sent_at"],
                log["event_type"],
                log["recipients"][:40],
                "yes" if log["dry_run"] else "no",
            )
        console.print(et)


def pick_rme(db: RmeDatabase, *, status: str | None = None) -> dict | None:
    records = db.list_all(status=status)
    print_rme_table(records)
    if not records:
        return None
    rid = Prompt.ask("Enter RME ID", default=str(records[0]["id"]))
    try:
        return db.get_by_id(int(rid))
    except (TypeError, ValueError):
        return db.get_by_rme_number(rid)


def action_create_rme(db: RmeDatabase, mail: RmeEmailService) -> None:
    console.print("\n[bold underline]Create RME[/]\n")
    rme_number = Prompt.ask("RME number")
    if db.get_by_rme_number(rme_number):
        console.print("[red]RME number already exists.[/]")
        return
    case_id = Prompt.ask("Case ID")
    partner_name = Prompt.ask("Partner name")
    part_number = Prompt.ask("Part number")
    quantity = IntPrompt.ask("Quantity", default=1)
    serial_number = Prompt.ask("Serial number")
    rme_type = Prompt.ask("RME type (optional)", default="")
    notes = Prompt.ask("Notes (optional)", default="")

    draft = {
        "rme_number": rme_number,
        "case_id": case_id,
        "partner_name": partner_name,
        "part_number": part_number,
    }
    email_subject = build_email_subject(draft)
    thread_id = build_thread_id(rme_number)

    console.print(f"\n[dim]Email subject (thread):[/] {email_subject}")
    if not Confirm.ask("Create RME and send notification emails?", default=True):
        return

    record = db.create_rme(
        rme_number=rme_number,
        case_id=case_id,
        partner_name=partner_name,
        part_number=part_number,
        quantity=quantity,
        serial_number=serial_number,
        rme_type=rme_type,
        email_subject=email_subject,
        email_thread_id=thread_id,
        notes=notes,
    )
    mail.notify_created(record, db)
    console.print(f"[green]RME {record['rme_number']} created (status: OPEN).[/]")
    print_rme_detail(record, db)


def action_list_open(db: RmeDatabase) -> None:
    console.print("\n[bold]Open RMEs[/]\n")
    print_rme_table(db.list_all(status="open"))


def action_view_rme(db: RmeDatabase) -> None:
    r = pick_rme(db)
    if r:
        print_rme_detail(r, db)


def action_mark_received(db: RmeDatabase, mail: RmeEmailService) -> None:
    console.print("\n[bold underline]Mark RME received (from vendor)[/]\n")
    r = pick_rme(db, status="open")
    if not r:
        return
    print_rme_detail(r, db)
    serial = Prompt.ask("Confirm serial number", default=r["serial_number"])
    try:
        updated = db.mark_received(r["id"], serial_number=serial)
    except ValueError as e:
        console.print(f"[red]{e}[/]")
        return
    if Confirm.ask("Send received email to all teams?", default=True):
        mail.notify_received(updated, db)
    console.print("[green]RME marked RECEIVED.[/]")
    print_rme_detail(updated, db)


def action_set_outbound(db: RmeDatabase) -> None:
    console.print("\n[bold underline]Set outbound number[/]\n")
    r = pick_rme(db, status="received")
    if not r:
        r = pick_rme(db, status="outbound_ready")
    if not r:
        return
    print_rme_detail(r, db)
    ob = Prompt.ask("Outbound number")
    try:
        updated = db.set_outbound(r["id"], outbound_number=ob)
    except ValueError as e:
        console.print(f"[red]{e}[/]")
        return
    console.print("[green]Outbound number saved.[/]")
    print_rme_detail(updated, db)


def action_mark_delivered(db: RmeDatabase, mail: RmeEmailService) -> None:
    console.print("\n[bold underline]Mark delivered & close RME[/]\n")
    r = pick_rme(db)
    if not r or r["status"] == "closed":
        if r and r["status"] == "closed":
            console.print("[yellow]RME is already closed.[/]")
        return
    print_rme_detail(r, db)
    outbound = Prompt.ask(
        "Outbound number",
        default=r.get("outbound_number") or "",
    )
    replacement = Prompt.ask("Replacement serial number")
    try:
        updated = db.mark_delivered(
            r["id"],
            replacement_serial_number=replacement,
            outbound_number=outbound,
        )
    except ValueError as e:
        console.print(f"[red]{e}[/]")
        return
    if Confirm.ask("Send closed/delivered email to all teams?", default=True):
        mail.notify_closed(updated, db)
    console.print("[green]RME CLOSED (delivered).[/]")
    print_rme_detail(updated, db)


def action_export_report(db: RmeDatabase) -> None:
    console.print("\n[bold underline]Export report[/]\n")
    choice = Prompt.ask(
        "Filter",
        choices=["all", "open", "received", "outbound_ready", "closed"],
        default="all",
    )
    status = None if choice == "all" else choice
    path = export_rme_report(db, status=status)
    console.print(f"[green]Report saved:[/] {path}")


def action_email_config(mail: RmeEmailService) -> None:
    console.print("\n[bold underline]Email configuration[/]\n")
    table = Table(box=box.SIMPLE)
    table.add_column("Setting")
    table.add_column("Value")
    table.add_row("Backend", mail.backend)
    table.add_row("From", mail.from_addr or "(Gmail profile)")
    table.add_row("SMTP host", mail.smtp_host or "(not set)")
    table.add_row("Dry run", "yes" if mail.dry_run else "no")
    table.add_row("On create (mgmt)", ", ".join(mail.mgmt_on_create) or "(not set)")
    table.add_row("On create (team)", ", ".join(mail.team_on_create) or "(not set)")
    table.add_row("All teams", ", ".join(mail.all_recipients) or "(not set)")
    console.print(table)
    console.print("\n[dim]Edit .env in this folder — see .env.example[/]")


MENU = [
    ("1", "Create RME", "create"),
    ("2", "List open RMEs", "list_open"),
    ("3", "View RME detail", "view"),
    ("4", "Mark received (vendor return)", "received"),
    ("5", "Set outbound number", "outbound"),
    ("6", "Mark delivered & close RME", "delivered"),
    ("7", "Export CSV report", "report"),
    ("8", "Email settings", "email_cfg"),
    ("0", "Exit", "exit"),
]


def main() -> None:
    db = RmeDatabase()
    mail = RmeEmailService()
    show_header()
    if mail.dry_run:
        console.print("[yellow]Email dry-run ON — messages print to terminal only.[/]\n")

    actions = {
        "create": lambda: action_create_rme(db, mail),
        "list_open": lambda: action_list_open(db),
        "view": lambda: action_view_rme(db),
        "received": lambda: action_mark_received(db, mail),
        "outbound": lambda: action_set_outbound(db),
        "delivered": lambda: action_mark_delivered(db, mail),
        "report": lambda: action_export_report(db),
        "email_cfg": lambda: action_email_config(mail),
    }

    while True:
        console.print()
        for key, label, _ in MENU:
            console.print(f"  [bold]{key}[/]  {label}")
        choice = Prompt.ask("Select", choices=[m[0] for m in MENU], default="1")
        if choice == "0":
            console.print("[dim]Bye.[/]")
            break
        action_key = next(a for k, _, a in MENU if k == choice)
        if action_key == "exit":
            break
        try:
            actions[action_key]()
        except KeyboardInterrupt:
            console.print("\n[dim]Cancelled.[/]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/]")


if __name__ == "__main__":
    main()

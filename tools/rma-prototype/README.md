# GoDaam RMA / RME Tracker (Prototype)

Standalone terminal UI on the VPS for tracking Return Merchandise Authorizations (RME).

**Not deployed** to production GoDaam — run locally on the server for testing before Koda/email integration.

## Workflow

| Step | Status | Action | Email |
|------|--------|--------|-------|
| 1 | `open` | Create RME (number, case ID, partner, part, qty, serial) | Ibrahim + Deepak; Jaigariya + Afar |
| 2 | `received` | Vendor return received — serial must match | All teams (same subject thread) |
| 3 | `outbound_ready` | Outbound number captured | — |
| 4 | `closed` | Delivered with replacement serial + outbound | All teams (same subject thread) |

Email subjects stay fixed per RME so replies stay in one thread (`Message-ID` / `In-Reply-To`).

## Run on VPS

```bash
ssh godam-vps
cd /root/GoDaam/tools/rma-prototype
chmod +x run.sh
./run.sh
```

## Configure email

Uses the **same Gmail OAuth as n8n**: credential `GAPP Gmail OAuth - Web Client` (`gmail.send` + `gmail.modify`).

```bash
cp .env.example .env
# RMA_EMAIL_BACKEND=gmail  (default)
# Set RMA_EMAIL_DRY_RUN=0 when ready to send for real
```

Verify Gmail access (no email sent):

```bash
.venv/bin/python test_gmail.py
```

Fallback: set `RMA_EMAIL_BACKEND=smtp` and fill SMTP fields in `.env`.

## Reports

Menu option **7** writes CSV to `exports/rme_report_*.csv`.

## Data

SQLite database: `data/rma.db`

## Next integration steps

1. Provide real SMTP settings (same as Koda mailbox).
2. Provide recipient email addresses.
3. Wire API routes into GoDaam `backend/` and a React page in `frontend/`.

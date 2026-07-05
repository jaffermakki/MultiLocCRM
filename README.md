# Tech-Pro+ CRM (Python / Flask rewrite)

Full rewrite of the original `TechPro_CRM_v2.html` single-page app into a responsive,
mobile-first Flask web app backed by a relational database (SQLite for local dev,
PostgreSQL for production — one config line to switch).

## What's included

Every module from the original HTML app, fully working and tested end-to-end:

- **PIN login** (tap your name, enter PIN) with role-based access (owner/manager/staff)
- **POS** — product grid, cart, customer lookup, Canadian tax calc (GST/PST/HST by province),
  loyalty points, store credit redemption, hold/recall carts, receipt printing
- **Repairs** — Kanban board (7 statuses), new ticket creation with inline customer creation,
  parts tracking, cost entry, one-click invoicing
- **Inventory** — CRUD, stock adjustments with audit trail, bulk supplier import (paste
  price-list text, preview, confirm)
- **Customers** — profile, notes, store credit issuance (by customer or by phone lookup),
  loyalty/credit ledgers with full transaction history, lifetime spend + last visit tracking,
  purchase and repair history
- **Reports** — date-range sales, tax collected, payment method breakdown, top products,
  repair turnaround stats, CSV/Excel export, printable End-of-Day report
- **Cash-Up** — open/close till sessions, automatic variance calculation against actual
  cash sales for that session
- **Refunds** — line-item refunds against any invoice, optional restock
- **Staff management** — add/edit/disable accounts, PIN reset (owner/manager only)
- **Audit Log** — append-only log of logins, sales, repairs, refunds, stock changes, etc.
- **Settings** — shop info, tax/province, invoice numbering, loyalty rates, email/SMS
  toggles, danger-zone data wipe

Fully responsive: sidebar nav collapses to a bottom tab bar + hamburger menu on phones.

## Loyalty program — exact mechanics

The loyalty/store-credit system was rebuilt to match the original app's real behavior
exactly (verified by reading the actual source, not guessed):

- **Earning**: points = `floor(final_invoice_total * points_per_dollar)`. This is
  calculated on the truly final total — after tax, after any store credit applied —
  and uses floor (rounds down), not round-to-nearest.
- **Redeeming at POS is locked to whole multiples** of "Points Needed for $1 Credit"
  (default 100). A customer with 250 points can redeem 100 or 200 — never 150 or 37.
  Requesting a non-multiple amount silently rounds **down** to the nearest valid
  multiple rather than rejecting the request.
- **Dollar value of redeemed points** = `points / points_redeem_rate`, not
  `points * some_rate`. With the default rate of 100, 100 points = $1.00.
- **Settings field names match the original UI exactly**: "Points Earned per $1 Spent"
  and "Points Needed for $1 Credit" — editing the second one changes the denominator
  in the formula above, it is not a per-point dollar price.
- **Manually issuing store credit** (Settings → Loyalty → "Manually Issue Store
  Credit") looks the customer up **by phone number**, matching the original's
  quick-issue workflow. Manual issues get a synthetic record number (e.g. `SC-A1B2C3`)
  so they're visible in the customer's transaction history even though no real sale
  occurred.
- **Lifetime spend** (`customer.spent`) and **last visit** are tracked and shown on
  the customer profile, separate from individual invoice records.
- Direct points→credit conversion (as opposed to redeeming at checkout) does **not**
  floor to a clean multiple — it converts the exact amount requested, matching the
  original's separate `redeemLoyaltyAsCredit` function.

## Quick start (local, SQLite — zero setup)

```bash
cd techpro_crm
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env              # defaults already point at SQLite, no edits needed

python seed.py                    # creates the database + a starter Owner/Staff account
python wsgi.py                    # runs on http://localhost:5000
```

Open `http://localhost:5000` on your phone or laptop browser. Seeded login PINs:

| Name  | PIN  | Role  |
|-------|------|-------|
| Owner | 1234 | owner |
| Sam Tech | 4321 | staff |

**Change these PINs immediately** if this will hold real data — go to Staff → Edit.

## Switching to PostgreSQL (production)

1. Create a database: `createdb techpro_crm`
2. In `.env`, set:
   ```
   DATABASE_URL=postgresql://user:password@localhost:5432/techpro_crm
   ```
3. Re-run `python seed.py` (it calls `db.create_all()`, which works against Postgres too).
   For ongoing schema changes after that, switch to Flask-Migrate:
   ```bash
   flask --app wsgi db init      # once
   flask --app wsgi db migrate -m "description"
   flask --app wsgi db upgrade
   ```

## Running on your phone over your local network

```bash
python wsgi.py    # already binds 0.0.0.0:5000
```
Then on your phone (same Wi-Fi), visit `http://<your-computer's-LAN-IP>:5000`.

## Multiple shop locations sharing one database

See `MULTI_LOCATION_SETUP.md` for the full walkthrough — each shop runs the app
locally (fast for staff, no internet dependency for the UI itself) while all
locations share one cloud Postgres database, so sales/repairs are visible
everywhere instantly. Includes setting up a free Neon Postgres database.

Once locations are configured (Settings → Locations) and staff are assigned to
one (Staff → Edit), **Reports → All Locations** gives a phone-friendly breakdown
of sales and repairs per shop — gated to owner/manager accounts.

## Running unattended on a Windows shop computer

See `deploy/windows/SETUP.md` for the full walkthrough — sets up the app to start
automatically when the computer boots (via Task Scheduler), survive crashes
(auto-restarts within 5 seconds), and run invisibly with no console window for
staff to accidentally close. Uses Waitress (`run_production.py`) instead of the
Flask dev server, since Waitress is meant to run unattended for long periods and
works natively on Windows (gunicorn does not).

## Deploying for free (so it's reachable from anywhere)

See `DEPLOY_FREE.md` for the full walkthrough — GitHub + Render (free app hosting) +
Neon (free, no-expiry database). Render's free tier sleeps after 15 minutes of
inactivity (30-60 second cold start on the next visit); upgrade to its $7/mo Starter
tier later if that becomes annoying. Includes a ready-to-use `render.yaml` Blueprint
so most of the setup is automatic.

## Project structure

See `app/` for the full breakdown: `models/` (database tables), `services/` (business
logic — tax calc, invoicing, loyalty, reports, imports), `blueprints/` (routes, one
folder per module), `templates/` (HTML), `static/` (CSS/JS).

## Known gaps vs. the original app

Found by reading the actual original source line-by-line (not guessed):

- **SMS (Twilio) and email receipts** are now fully built with support for multiple
  providers — see the section below.
- **Photo uploads for repairs** (`RepairPhoto` model exists) don't have an upload UI yet.
- **Refunds don't recalculate tax** — a refund here returns the flat per-item price;
  the original recalculates proportional tax on the refunded subtotal and can also
  pay refunds out as store credit, not just restock-and-done.
- The bulk import parser in `app/services/inventory_import.py` is a best-effort,
  permissive parser — if your real supplier export has a specific format, tell me
  and I'll tighten it to match exactly instead of guessing.

**Fully verified working and matching the original's exact mechanics:** PIN auth +
role gating, POS checkout with Canadian tax/split payment/cash tendered+change,
inventory + bulk import, customers, **the complete loyalty/store-credit system**
(locked redemption multiples, floor-based earning, phone-lookup manual issue, lifetime
spend tracking), reports/exports, cash-up with session-linked variance calculation,
basic refunds, staff management, audit log, settings, multi-location support with
independent per-location stock counts and day-by-day/month-by-month location
comparison, **and the complete repairs module** — sequential ticket numbers starting
at 1001, assigned technicians, the three-stage cost model (estimated → approved →
final, with the same `final || approved || estimated || 0` waterfall used for
invoicing), promised-completion dates with overdue detection, full timestamped status
history, warranty tracking (default 90 days, checked off the actual COMPLETED
timestamp in that history — not ticket creation date) with a live phone-lookup
warranty-return warning when creating a new ticket, a COMPLETED-without-cost
confirmation guard, SKU-based parts lookup that deducts stock immediately, and the
dashboard's 7-day sales chart + repairs-by-status breakdown + overdue-repairs banner.

## SMS and email notifications

Both are fully built with a swappable provider architecture — switching from Twilio
to Vonage, or from SendGrid to Mailgun, is a Settings page change, not a code change.

**What actually sends automatically:**
- **"Ready for Pickup" SMS** — sent automatically when a repair ticket moves to
  "Ready for Pickup" status. Uses the template in Settings → SMS (supports
  `{customer_name}`, `{device}`, `{shop_name}` placeholders).
- **Email receipt** — an "Email Receipt" button appears on every invoice page for
  customers who have an email address on file. Not sent automatically at checkout
  (you click it when the customer asks), but can be made automatic trivially by
  calling `send_receipt_email(invoice)` after `complete_sale()` if you want that.

**Supported email providers:**

| Provider | Required `.env` variables |
|---|---|
| SMTP (Gmail, Outlook, Zoho, any relay) | `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD` (+ optional `SMTP_PORT`, `SMTP_USE_SSL`) |
| SendGrid | `SENDGRID_API_KEY` |
| Mailgun | `MAILGUN_API_KEY`, `MAILGUN_DOMAIN` (+ optional `MAILGUN_REGION`) |
| Postmark | `POSTMARK_SERVER_TOKEN` |
| Amazon SES | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` + `pip install boto3` |

**Supported SMS providers:**

| Provider | Required `.env` variables |
|---|---|
| Twilio | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` |
| Vonage (Nexmo) | `VONAGE_API_KEY`, `VONAGE_API_SECRET` |
| MessageBird | `MESSAGEBIRD_API_KEY` |
| Telnyx | `TELNYX_API_KEY` (+ optional `TELNYX_MESSAGING_PROFILE_ID`) |
| Amazon SNS | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` + `pip install boto3` |

For all providers, also set `EMAIL_FROM_ADDRESS` and `EMAIL_FROM_NAME` in `.env`
(these are shared across email providers — only the credentials differ).
Set `sms_from_number` in Settings → SMS (the From Number / Sender ID field).

**Switching providers:** Go to Settings → Email or Settings → SMS, pick the new
provider from the dropdown, save — done. Credentials for the new provider must
already be in `.env`. A "Send Test" button is on both tabs so you can verify a
provider works before relying on it for real traffic.

**Adding a new provider not listed above:** Write one new class in
`app/services/notifications/` implementing `EmailProvider` or `SMSProvider`
(see `base.py` for the interface, any existing file for the pattern), then add
one line to `EMAIL_PROVIDERS` or `SMS_PROVIDERS` in `__init__.py`. Nothing else
in the app needs to change.

## Printing

Every invoice has two print formats, cross-linked from each other:

- **Full invoice** (`/pos/receipt/<id>`) — standard letter/A4 layout for emailing
  or filing.
- **80mm thermal receipt** (`/pos/receipt/<id>/thermal`) — formatted for a real
  thermal roll printer, not just narrowed on screen. Uses a CSS `@page { size: 80mm
  auto; margin: 0; }` rule, which is what actually controls thermal printer output;
  without it, browsers default to assuming Letter/A4 paper and add margins plus a
  header/footer that thermal paper has no room for. Same totals and line items as
  the full invoice, plus the cashier's name and payment method (standard on a POS
  receipt, even though the full invoice doesn't show them).

To print to a real receipt printer, open the thermal version, hit Print, and select
your thermal printer in the OS print dialog the same way you would for any other
print job — no special driver setup needed beyond what your printer already requires
for normal printing.

## Multi-location inventory and reporting

Once you've added locations (Settings → Locations) and assigned staff to one
(Staff → Edit), two things change:

- **Stock is tracked per location, not catalog-wide.** The same product (same SKU,
  name, price) can have different quantities on hand at each shop. Selling the last
  unit at Downtown does not affect Westside's count for that same product — each
  location's stock is its own independent number. The Inventory page shows one
  column per location; "Adjust Stock" and bulk imports both require picking which
  location the change applies to.
- **Reports → All Locations** (owner/manager only) shows a snapshot for any date
  range, split per shop, plus **"Compare Over Time"** — a day-by-day or
  month-by-month chart and table showing each location's sales trending against the
  others, not just a single range's total. Useful for spotting things like "Westside
  is growing faster than Downtown this quarter" rather than just a one-time total.

Note: customers and the product catalog itself (name, price, cost, SKU) are still
shared across all locations — only stock quantity is per-location. If you later want
fully separate customer lists or pricing per shop, that's a bigger change; ask and
I'll scope it out.

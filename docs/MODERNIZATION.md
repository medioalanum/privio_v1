# Modernization audit

Baseline: 98f01311b7eeae930924d54b768078cc3c1cdf2c; working branch:
`modernization/monthly-cashflow`. Local checkout: `/Users/alanviana/Projects/privio_v1`.

## Confirmed from source

Python >=3.11, uv.lock, FastAPI, SQLAlchemy, PostgreSQL/psycopg,
Jinja2, HTMX 2.0.2, Pico CSS; PT/EN/IT. Tests use isolated SQLite.
The baseline has no Alembic history or CI workflow. Existing migrations are
SQLAlchemy create_all and inspector-guarded ALTER TABLE statements at startup.
Render blueprint names privio-commitments-app. Authenticated settings confirmed
main auto-deploys on commits; merging is treated as a release action.

Persisted models: commitments, dated adjustments, payments, deposits, accounts,
internal transfers. No attachment/file storage appears in source. Authenticated Render inspection confirmed no persistent disk (free plan), no
secret files, and Neon PostgreSQL 18.6 as the sole application data store.

## Problems addressed

- Startup silently catches database errors and synthesizes legacy payments with
  assumed payment dates/accounts. Move schema preparation to an explicit,
  repeatable command; do not synthesize historical transactions.
- Month calculations mix payment date with due month; distinguish realized
  cash movements and settlement of scheduled occurrences.
- Annual obligations are subtracted from resources and labeled free-to-spend.
  Replace primary cards with monthly decisions and daily cash flow.
- Boolean estimate=false cannot establish confirmation. Legacy amounts must
  remain unclassified unless explicit confirmation is recorded.
- Payment writes need serialization, validated accounts/amounts and duplicate
  conflict handling. Internal transfer validation needs row locks.
- No upcoming income model exists. Do not pretend received deposits are expected
  income. Show missing forecast inputs explicitly.

## Delivery gates

Implement and test with synthetic data, then validate desktop/mobile internally.
Before production: authenticated service inspection; consistent backup of all
persistent stores outside repository/ephemeral storage; isolated restore and
record-by-record comparison; migration rehearsal twice; explicit write-control
window; candidate checks; compatible application rollback preserving new writes.
A code rollback must never restore an old database automatically.

Release evidence is recorded below. Production is not modified by ordinary tests.

## Baseline validation

Python 3.12.14 installed in isolated managed runtime; uv 0.12.10 installed in a
workspace venv; 38 packages installed with `uv sync --frozen --all-groups`.
Original tests: 33 passed, 1 failed (test_web recurrence test assumes current
month August 2026). Ruff lint and ty pass. Format check fails in app/auth.py.

## Hosting verified (authenticated Render dashboard)

Service srv-da688hmk1f9s73di8csg, Python free instance, Oregon, managed by
Blueprint. Published main at baseline 98f01311b7eeae930924d54b768078cc3c1cdf2c.
Latest live deploy dep-da6jr6rm8hqs738niq00 (2026-08-25) was Auto-Deploy.
Build/start match render.yaml; /health configured. Pre-deploy commands and
maintenance mode are unavailable on this instance. DATABASE_URL is configured;
Neon provider and recovery access were verified without publishing credentials.

## Candidate validation (2026-09-08)

- Consistent PostgreSQL custom backup with exported repeatable-read snapshot;
  private SHA-256 manifest checks every original field of every row.
- Restored to a separately named database on the existing endpoint; every original
  record matched. No new service, plan, or endpoint was created.
- Migration repeated twice on the restored database; all original rows unchanged.
- Compatible rollback revision `ba1e63b7a909aba72cb658377fe6201c4c8c53a8`
  on `rollback/modernization-safe-start`; old dashboard/health smoke passed against
  the restored database with read-only transactions and no startup backfill.
- SQLite: 44 passed, 1 skipped (PostgreSQL-only concurrency), one upstream
  Starlette/httpx deprecation warning. PostgreSQL: all 45 tests passed, including
  simultaneous duplicate payments. No dependency changes were required.
- Ruff lint/format, ty, and whitespace checks passed. GitHub Quality CI added.
- Internal browser: synthetic desktop/mobile (390px), month navigation, filters,
  empty results, successful payment with stable projection, PT/EN/IT, dialog focus,
  Shift+Tab wrap and Escape. No horizontal page overflow at mobile width.
- Production-equivalent frozen/no-dev installation and scripts/start.sh succeeded
  against the restored PostgreSQL database. Internal browser verified monthly
  navigation, four cards and annual disclosure on that staging instance.
- Docker image build was not run (Docker unavailable); Render uses the tested
  native Python start path. Backup comparisons and real data remain private.
- Remote main remained at baseline before candidate commit. No branch protection
  rules were returned by GitHub; CI is still required by the release procedure.

The dashboard deliberately leaves balances/projections unknown when legacy
accounts or payment records are insufficient. Confirmation is explicit per
occurrence, never inferred from a missing estimate flag. Past expected income is
excluded. Expected income supports creation and one receipt; rescheduling/cancel
of expectations is not included in this release. Payment settlement preserves the
existing one-payment model; it does not add cumulative partial payments.

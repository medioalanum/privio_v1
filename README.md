# Privio

Privio is a financial commitment and reserve management application built with
FastAPI, SQLAlchemy 2.0, PostgreSQL, Jinja2, and HTMX. It provides a
server-rendered dashboard, a REST API, role-based access control, recurring
commitment projections, per-occurrence adjustments, and deposit tracking.

## Experimente o Privio / Try the demo

**[Abrir demonstração pública / Open public demo](https://privio-demo.onrender.com/)**

Escolha o perfil na tela de login e informe a senha abaixo. / Choose a role on the
login screen and enter the password below.

| Perfil / Role | Senha / Password | O que pode fazer / Permissions |
| --- | --- | --- |
| **Admin** | `test` | Criar, editar e excluir contas; registrar pagamentos e receitas; consultar e exportar PDFs. / Manage fictional records and export reports. |
| **Client** | `test` | Consultar contas, saldos e previsões; exportar o relatório mensal. / Browse and export reports; no editing. |

Para chamadas de API com autenticação Basic, os usuários são `admin` e `client`,
ambos com senha `test`, **somente neste ambiente demo**.

- Todos os dados são fictícios. **Não insira informações reais.**
- A demonstração é compartilhada: alterações de um visitante aparecem para outros.
- Os exemplos são restaurados diariamente, por volta de **03:17 UTC**. Alterações
  não são permanentes; o agendamento pode sofrer atrasos.
- Hospedada no Render gratuito: o primeiro acesso após inatividade pode levar
  cerca de um minuto. Aguarde o serviço iniciar.
- O ambiente de uso real utiliza contas, banco e credenciais independentes.

All data is fictional and shared. Do not enter real information. Examples reset
around 03:17 UTC daily; changes are temporary. The first visit after inactivity
may take about a minute while the free service starts.

### Telas da demonstração / Demo screenshots

Capturas com dados fictícios; os valores exibidos podem mudar após a restauração.

![Login da demonstração, com instruções de acesso](docs/images/demo-login.png)

![Dashboard Admin com contas fictícias e ações de gerenciamento](docs/images/demo-admin.png)

![Visão Client em tema claro, com saldos e previsão](docs/images/demo-client.png)

<details>
<summary>Exemplo do relatório mensal em PDF</summary>

![Relatório mensal identificado como demonstração](docs/images/demo-report.png)

</details>

See [demo operations](docs/DEMO_OPERATIONS.md) for provisioning, controlled releases,
reset recovery and account separation.

## Features

- Branded browser login with secure, signed, HTTP-only session cookies.
- **Admin** operational dashboard and **Client** read-only overview, with
  canonical login names configured through environment variables.
- Commitment recurrence: weekly, monthly, semiannual, and annual.
- Edit a single occurrence, the selected occurrence and all future ones, or the
  entire recurring series.
- Delete one occurrence or the complete recurring series.
- Three primary monthly indicators: remaining bills, money available now, and
  the shortfall or surplus after paying. Current-month bills include older
  unpaid occurrences once.
- Next due-date totals, collapsible search and filters, and daily subtotals.
- Client coverage bar and six-month rolling cash forecast, with text values
  and a detailed table; unknown balances do not produce misleading charts.
- Calendar-month navigation that is preserved across HTMX actions.
- Actual payment records with separate due date, payment date, paid amount, and
  optional notes.
- Exact 12-month forecast with full semiannual and annual bills in their due
  months instead of monthly averages.
- Freely named financial accounts and wallets, including bank accounts,
  prepaid cards, cash, and money managed by third parties.
- External inflows increase total resources, while internal transfers only
  redistribute money and never duplicate the total.
- Payments are linked to the account that funded them, enabling accurate
  current account balances when account assignments and ledger data are complete.
- Portuguese, English, and Italian dashboard translations.
- Server-rendered UI with Jinja2, HTMX, and Pico.css.
- OpenAPI documentation through FastAPI Swagger UI and ReDoc.

## Technology Stack

- Python 3.11+
- [FastAPI](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0](https://www.sqlalchemy.org/)
- [PostgreSQL](https://www.postgresql.org/) with psycopg 3
- [Pydantic v2](https://docs.pydantic.dev/) and pydantic-settings
- [Jinja2](https://jinja.palletsprojects.com/) and [HTMX](https://htmx.org/)
- [Pico.css v2](https://picocss.com/)
- [uv](https://docs.astral.sh/uv/) for dependency management
- [Ruff](https://docs.astral.sh/ruff/) for linting and formatting
- [ty](https://github.com/astral-sh/ty) for static type checking
- pytest and HTTPX for automated tests

## Project Structure

```text
privio_v1/
├── app/
│   ├── models/              # SQLAlchemy models and recurrence adjustments
│   ├── routers/             # REST API and server-rendered UI routes
│   ├── schemas/             # Pydantic request and response schemas
│   ├── services/            # Recurrence and reserve calculations
│   ├── templates/           # Jinja2 dashboard and login templates
│   ├── auth.py              # Basic Auth, browser sessions, and RBAC
│   ├── config.py            # Environment-based application settings
│   ├── database.py          # SQLAlchemy engine and session management
│   ├── i18n.py              # Portuguese, English, and Italian translations
│   └── main.py              # FastAPI application entry point
├── docs/                    # Financial definitions, operations, and staged releases
├── scripts/                 # Quality checks and maintenance utilities
├── tests/                   # Unit and integration tests
├── .env.example             # Environment variable template
├── Dockerfile               # Production container image
├── render.yaml              # Render Blueprint definition
├── fly.toml                 # Fly.io configuration
├── pyproject.toml           # Project and tool configuration
└── uv.lock                  # Reproducible dependency lockfile
```

## Local Setup

### 1. Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Update `.env` with your PostgreSQL connection and private credentials:

```ini
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/privio_db

APP_NAME=Privio Commitments API
ENVIRONMENT=development
DEBUG=true
HOST=0.0.0.0
PORT=8000

# Canonical login names
ADMIN_USER=admin
CLIENT_USER=client

ADMIN_PASS=replace-with-a-strong-password
CLIENT_PASS=replace-with-a-strong-password
SESSION_SECRET=replace-with-a-long-random-value
PREVIEW_MODE=false
```

Never commit `.env`, production passwords, database connection strings, or the
session secret. Use a separate development database and private development
credentials; production credentials are not demo credentials. `PREVIEW_MODE=true`
only adds a demonstration notice. It does not seed data, isolate a database,
change permissions, or create credentials. Keep it disabled in production.

### 3. Install dependencies

```bash
uv sync --frozen --all-groups
```

### 4. Prepare the schema and start the development server

```bash
uv run python -m scripts.migrate
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open the following pages:

- Dashboard: <http://localhost:8000/>
- Login: <http://localhost:8000/login>
- Swagger UI: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>

Production uses `sh scripts/start.sh`, which runs the additive migration
explicitly before serving.
Startup does not infer or create historical payments.

## Authentication and Roles

The browser UI uses a branded login page and a signed session cookie. The REST
API also accepts HTTP Basic Auth for scripts and external clients.

| Profile | Canonical username | Password setting | Access |
|---|---|---|---|
| **Admin** | `ADMIN_USER` (default `admin`) | `ADMIN_PASS` | Read, create, edit, register payments and inflows, manage accounts and recurring rules |
| **Client** | `CLIENT_USER` (default `client`) | `CLIENT_PASS` | Read-only overview and permitted data; mutations return HTTP 403 |

On the browser login page, select **Admin** or **Client** and enter the
corresponding password. Authentication and signed sessions use only the canonical
`admin` and `client` roles. Retired aliases and sessions containing retired roles
are rejected; sign in again once after migration using the same passwords.
Session usernames must match the configured account for their role. Cookies remain
HTTP-only, SameSite=Lax and Secure in production. No accounts or financial records
are migrated in the database.

Production requires explicit `ADMIN_PASS`, `CLIENT_PASS` and `SESSION_SECRET`;
missing secrets or development defaults stop startup instead of granting access.
Admin and Client login names must be distinct. Never log or commit passwords.

## Monthly Dashboards and Financial Definitions

Both profiles use the same calculation service, [decisions.py](app/services/decisions.py).
The current month is the default. Open the month label to choose another month,
or use the previous/next controls; the selected month is kept across HTMX actions.

### Three primary indicators

| Indicator | Meaning |
|---|---|
| **To pay by month end** | For the current month, all remaining occurrences due through month end, including older unpaid bills exactly once |
| **Money available now** | Active-account opening balances plus posted ledger movements through today; expected receipts are excluded |
| **Still needed / Left after paying** | Current available money minus the remaining total; shown only for the current month when the balance is verifiable |

When browsing a past or future month, the bills list uses that month's due dates,
without rolling earlier unpaid bills into the primary total. The cash figure is
still today's balance, not a reconstructed historical balance or a future opening
balance; the shortfall/surplus card is therefore left unset outside the current
month. Use the forecast for future cash positions.

### Admin: operate the current month

- Pending bills are ordered by due date and include earlier arrears in the
  current-month view. The next due-date alert sums every pending occurrence on
  that date instead of showing only the first bill.
- Daily subtotals follow the filtered list when sorted by date. Amount sorting
  presents a ranked list instead of date groups.
- Search, status, category, amount classification, account, responsible person,
  and sort controls are collapsible. Filters affect the list and its subtotal,
  not the primary overall indicators. Account/responsible filters use recorded
  payment assignments; unpaid items without a payment are unassigned.
- Register a payment from the occurrence; access editing and other actions in
  its details. Paid bills in the selected due-date month are available via
  **View paid bills**. The system settles an occurrence with one payment record;
  it does not implement cumulative partial payments.
- Account management, recurring rules, and detailed cash flow are secondary
  sections. Expected income is separate from actual deposits and can be
  received once without counting both the expectation and deposit as cash.

### Client: understand coverage and future needs

- A short current-month summary explains whether current funds cover the bills.
- A coverage bar compares available money with pending obligations, capped
  between 0% and 100%. Coverage is not the percentage already paid. With a known
  balance and no pending bills, coverage is 100%; any cash surplus remains visible.
- Payment details are collapsed; account management and recurring-rule controls
  are absent. Read-only restrictions also apply on the server.
- The six-month forecast is visible in the overview. Admin can expand the same
  forecast from a secondary section. Chart values are available as text and in
  a detailed table, including when color alone is insufficient.
- **Calculated on** indicates the date of calculation, not an independently
  verified bank reconciliation or last update by the Admin.

### Two different forecasts

The **six-month cash forecast** always starts in the actual current month,
independently of the month selected in the bills list. Its first opening value
is today's known balance. Earlier pending bills enter the first forecast month
once. Each closing balance becomes the following month's opening balance:

```text
Projected closing balance = opening balance + expected income - pending bills
```

Only unreceived, non-overdue expected income assigned to an active EUR account
is included for its expected date. A notice identifies the absence of registered
future income; that absence is not proof that no money will arrive. The dated
cash-flow detail places overdue payments on today without changing their due
dates. A month-end surplus alone does not prove that every earlier date is funded.

The secondary **12-month payment schedule** starts in the selected month and
shows full scheduled bills, including annual and semiannual amounts in their due
months. It is an obligations schedule, not a forecast of free cash.

### Estimates and unknown balances

Estimates remain included and identified. Legacy values without an explicit
review stay unclassified; they are not automatically confirmed. The estimate
subtotal follows the same scope as the primary remaining-bills total.

The balance and dependent projections stay unknown when there are no usable
accounts, only an allocation account, unsupported currencies, movements that
cannot be assigned to an active account, or legacy paid statuses without payment
records. Consolidation currently supports EUR only; no implicit FX conversion is
performed. Opening balances must be consistent with the posted ledger to avoid
counting movements twice.

Admin sees **Review balances** linking to the accounts section. Client sees that
Admin review is needed. Opening this section does not reconcile data automatically.
The application does not invent cash, dates, receipts, or historical payments to
fill missing indicators.

See [financial definitions and operations](docs/OPERATIONS.md) and the
[Admin/Client staged release plan](docs/ADMIN_CLIENT_RELEASES.md).
[MODERNIZATION.md](docs/MODERNIZATION.md) records the earlier baseline diagnosis.

## Recurring Commitment Changes

Recurring commitments support three edit scopes:

- **This occurrence only:** creates a dated exception without changing other
  months.
- **This and future occurrences:** applies a dated rule from the selected
  occurrence onward.
- **Entire series:** updates the base commitment, including its historical
  representation.

Users may also delete one projected occurrence or delete the complete series.
Occurrence exceptions are stored separately from the base commitment so future
projections remain consistent.

## Internationalization

The dashboard supports a URL language parameter and a header selector:

- Portuguese: `/?lang=pt`
- English: `/?lang=en`
- Italian: `/?lang=it`

Unsupported values fall back to Portuguese.

## API Overview

### Commitments

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/commitments` | Create a commitment |
| `GET` | `/commitments` | List and filter commitments |
| `GET` | `/commitments/{id}` | Retrieve one commitment |
| `PUT` | `/commitments/{id}` | Fully replace a commitment |
| `PATCH` | `/commitments/{id}` | Partially update a commitment |
| `DELETE` | `/commitments/{id}` | Delete the complete commitment series |
| `GET` | `/upcoming?days=30` | Project upcoming occurrences |
| `GET` | `/suggested-monthly` | Calculate the suggested monthly budget |

### Deposits

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/deposits` | Record a deposit |
| `GET` | `/deposits` | List deposits |
| `GET` | `/deposits/{id}` | Retrieve one deposit |
| `PUT` | `/deposits/{id}` | Fully replace a deposit |
| `PATCH` | `/deposits/{id}` | Partially update a deposit |
| `DELETE` | `/deposits/{id}` | Delete a deposit |
| `GET` | `/reserve-balance` | Calculate the current reserve balance |

## Quality Checks

Run all configured checks:

```bash
./scripts/check.sh
```

Or run them individually:

```bash
uv run ruff check .
uv run ruff format --check .
uv run ty check .
uv run pytest
```

By default, tests use isolated in-memory SQLite. The CI workflow also runs the
suite against PostgreSQL 18, including the concurrent payment test skipped on
SQLite. To test PostgreSQL locally, set `PRIVIO_TEST_DATABASE_URL` to an isolated,
disposable database whose name starts with `privio_test_`, then run `uv run pytest`.
The fixture creates and drops tables: never use production or a database holding
records you need to retain.

Tests cover authentication and retired-alias rejection, Client write restrictions,
recurrences, monetary calculations, payment idempotency, month boundaries,
coverage, rolling forecasts, and record preservation across dashboard reads and
repeated migrations. See [.github/workflows/checks.yml](.github/workflows/checks.yml)
for the current CI configuration.

## Production Deployment

The repository includes production configuration for Render and Fly.io and is
compatible with Neon PostgreSQL.

### Render and Neon

1. Create a Neon project and copy its pooled PostgreSQL connection string.
2. Connect this repository to Render as a Blueprint.
3. Set `DATABASE_URL` in the Render dashboard.
4. `render.yaml` configures `ADMIN_USER=admin` and `CLIENT_USER=client`.
   Set `ADMIN_PASS` and `CLIENT_PASS` explicitly; preserve their current values
   during migration. Keep `SESSION_SECRET` unchanged. The Blueprint does not
   regenerate passwords when their keys change.
5. Deploy and verify `/health`.

The application normalizes standard `postgresql://` URLs for psycopg 3 and uses
connection health checks suitable for serverless PostgreSQL.

For an existing installation, the linked `main` branch auto-deploys. Treat merge
as a release action: pass CI, validate the candidate, take a consistent backup,
and prove restoration in an isolated database before a functional release.
Compare preserved records before and after publication, confirm the deployed
commit and `/health`, and monitor the service. Publish dependent phases one at a
time. Tests passing alone do not prove that production data is recoverable.

The Admin/Client releases do not change the database schema or rewrite stored
records. The startup migration remains additive. Roll back compatible application
code while preserving the live database; restoring an old backup automatically
could erase subsequent legitimate records. Keep backups and manifests outside
Git with restricted access.

See [DEPLOYMENT.md](DEPLOYMENT.md) for hosting setup,
[OPERATIONS.md](docs/OPERATIONS.md) for migration, backup, restore, and rollback
procedures, and [ADMIN_CLIENT_RELEASES.md](docs/ADMIN_CLIENT_RELEASES.md) for the
role-specific release sequence.

## License and Copyright

Privio © 2026 — All rights reserved.

## Monthly PDF report

Both Admin and Client can select a month and choose **Download monthly report
(PDF)** beside the month navigation. The report follows the selected dashboard
language (Portuguese, English or Italian) and includes every bill due in that
calendar month, independently of search, status and other list filters. Earlier
arrears and the following month's bills are excluded explicitly.

The payer-focused PDF shows the amount left to pay, actual recorded payments and
the combined monthly total, followed by pending bills ordered by due date and
paid bills with their payment dates. Overdue bills, bills due today and estimated
amounts are identified in text. Payments belong to the bill's due-date month even
when paid in another month. A recorded payment settles an occurrence at its actual
paid amount; future-dated payments are not yet treated as paid. Legacy paid
statuses without payment records show missing details and incomplete totals,
never invented payment amounts or dates.

Each download is a fresh snapshot with an explicit UTC export timestamp. It is
built in memory, sent as an attachment with `Cache-Control: private, no-store`,
and is not saved or retained by Privio. Downloaded files remain on the user's
device. This is a view of the current records, not a historical reconstruction or
a bank receipt. PostgreSQL exports use a repeatable-read, read-only transaction.
No schema, account, payment, balance or credential changes are required.

The authenticated endpoint is `GET /reports/monthly.pdf?month=YYYY-MM&lang=pt`.
ReportLab is a locked runtime dependency with no browser or external rendering
service required. Regression coverage in `tests/test_monthly_report.py` checks
month boundaries, actual paid amounts, unknown legacy values, recurrence,
permissions, record preservation and pagination in all supported languages.

## Header navigation and languages

The left menu contains Swagger API for Admin and sign out for both profiles.
The Privio brand returns to the dashboard. The current language stays at the right;
PT/EN/IT alternatives open to its left by mouse hover, click, touch or keyboard.
Escape closes the selector/menu and returns focus. Language links preserve the
selected month and list filters; an unsaved form prompts before navigation.
Financial records, access permissions and report calculations are unchanged.

## Appearance and sign-in

The menu offers Automatic (default), Light and Dark. Automatic follows the device;
explicit choices persist only in this browser under `privio-theme`. The theme is
applied before painting and changes immediately without reloading, submitting
forms or touching financial records. Storage restrictions fall back gracefully.
The PDF retains its white print layout independently of the screen theme.

Sign-in uses a two-column layout: a decorative calendar/payment illustration on
the left and the access form on the right. Small screens hide the illustration
and prioritize the form. Language is available before login; the login screen always uses the dark palette
and has no hamburger menu or appearance controls. This does not overwrite the
user’s saved theme for authenticated pages.
Password visibility is an explicit button; failed login keeps the selected role
and language, clears the password, and announces a translated error. Current
credentials and permissions are unchanged by this presentation release.

## Admin/Client credential migration

Prepare the new password keys in Render with the existing values using **Save
only**, while the prior application remains running. Deploy this version and
verify both logins, Client write denial, dashboards and PDF downloads. Then remove
the retired user/password keys from Render, keeping ADMIN_USER, ADMIN_PASS,
CLIENT_USER and CLIENT_PASS for these accounts. No password or SESSION_SECRET
rotation is required. Old browser sessions require a fresh sign-in. Update external
Basic Auth clients still using retired login names before switching.

Code rollback must also restore the credential-key configuration expected by the
prior version before redeployment, using the preserved values. Never restore an old
financial database to roll back authentication or appearance.

## Mobile menu behavior

The menu stays open while interacting with its links and theme radios, including
touch browsers that emit focus loss without a related target. Close it with its
summary, an outside tap/click, or Escape. The shared green accent applies to the
brand, links, buttons, focus rings and selected controls in both themes.

Run JavaScript interaction regressions with Node 22+:
`node --test tests/browser/*.test.mjs` (also required in CI), alongside `uv run pytest`.

## Public demo isolation

`DEMO_MODE` defaults to false. Only the separate public demo enables it; both demo
profiles use password `test`. Production rejects this public password when demo
mode is off. Public credentials never grant access to Render, Neon or the company
application.

`python -m scripts.demo` initializes an empty, explicitly pinned demo database once.
Subsequent starts preserve visitor changes. `python -m scripts.demo --reset`
atomically replaces examples only after a demo marker exists. Both commands refuse
other database endpoints before connecting. Reset preserves primary-key sequences
so stale browser forms cannot modify a new example under a recycled ID.

Demo PDFs and pages are labeled fictional. The demo is shared: visitors see each
other's edits. Do not enter real information. Financial data and credentials from
the company environment must never be copied into the demo or screenshots.

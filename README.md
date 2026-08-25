# Privio

Privio is a financial commitment and reserve management application built with
FastAPI, SQLAlchemy 2.0, PostgreSQL, Jinja2, and HTMX. It provides a
server-rendered dashboard, a REST API, role-based access control, recurring
commitment projections, per-occurrence adjustments, and deposit tracking.

## Features

- Branded browser login with secure, signed, HTTP-only session cookies.
- Editor and viewer roles configured through environment variables.
- Commitment recurrence: weekly, monthly, semiannual, and annual.
- Edit a single occurrence, the selected occurrence and all future ones, or the
  entire recurring series.
- Delete one occurrence or the complete recurring series.
- Month-by-month cash flow with received, scheduled, paid, pending, available,
  and projected amounts.
- Calendar-month navigation that is preserved across HTMX actions.
- Actual payment records with separate due date, payment date, paid amount, and
  optional notes.
- Exact 12-month forecast with full semiannual and annual bills in their due
  months instead of monthly averages.
- Freely named financial accounts and wallets, including bank accounts,
  prepaid cards, cash, and money managed by third parties.
- External inflows increase total resources, while internal transfers only
  redistribute money and never duplicate the total.
- Payments are linked to the account that funded them, enabling an accurate
  total-resources and free-to-spend position.
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

EDITOR_USER=editor
EDITOR_PASS=replace-with-a-strong-password
VIEWER_USER=viewer
VIEWER_PASS=replace-with-a-strong-password
SESSION_SECRET=replace-with-a-long-random-value
```

Never commit `.env`, production passwords, database connection strings, or the
session secret.

### 3. Install dependencies

```bash
uv sync --all-groups
```

### 4. Start the development server

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open the following pages:

- Dashboard: <http://localhost:8000/>
- Login: <http://localhost:8000/login>
- Swagger UI: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>

Database tables are created during application startup with
`Base.metadata.create_all()`.

## Authentication and Roles

The browser UI uses a branded login page and a signed session cookie. The REST
API also accepts HTTP Basic Auth for scripts and external clients.

- **Editor:** read access plus creation, editing, status changes, and deletion.
- **Viewer:** read-only access to the dashboard, commitments, projections, and
  reserve balance. Mutation attempts return HTTP 403.

The session cookie is HTTP-only, uses `SameSite=Lax`, and is marked `Secure` in
production. Passwords remain in environment variables and are never stored in
the cookie.

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

Tests use an isolated in-memory SQLite database.

## Production Deployment

The repository includes production configuration for Render and Fly.io and is
compatible with Neon PostgreSQL.

### Render and Neon

1. Create a Neon project and copy its pooled PostgreSQL connection string.
2. Connect this repository to Render as a Blueprint.
3. Set `DATABASE_URL` in the Render dashboard.
4. Render generates editor, viewer, and session secrets from `render.yaml`.
5. Deploy and verify `/health`.

The application normalizes standard `postgresql://` URLs for psycopg 3 and uses
connection health checks suitable for serverless PostgreSQL.

See [DEPLOYMENT.md](DEPLOYMENT.md) for the complete deployment guide.

## License and Copyright

Privio © 2026 — All rights reserved.

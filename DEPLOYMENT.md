# Deployment: Render or Fly.io with Neon PostgreSQL

This guide explains how to deploy Privio using Neon for PostgreSQL and Render or
Fly.io for the application. Repository configuration files are the reference for
build and startup commands. Check provider plan limits before provisioning.

## 1. Create the Neon database

1. Sign in to [Neon](https://neon.tech) and create a project.
2. Choose a project name, a supported PostgreSQL version, and a region close to
   the application service. The public demo uses PostgreSQL 18.
3. Open the connection details and select a pooled connection.
4. Copy the connection string into the hosting provider's secret settings.

Example format, with placeholders only:

```text
postgresql://USER:PASSWORD@HOST/neondb?sslmode=require
```

Privio normalizes the PostgreSQL URL to use the psycopg driver. Never commit a
real connection string to Git. Use a dedicated development database for local work.

## 2. Deploy on Render

### Blueprint setup

1. Push the repository to GitHub or GitLab.
2. Open the [Render Dashboard](https://dashboard.render.com/) and create a Blueprint.
3. Connect the repository and review [render.yaml](render.yaml).
4. Supply `DATABASE_URL`, `ADMIN_PASS`, and `CLIENT_PASS` when prompted.
   The Blueprint generates `SESSION_SECRET` for a new service. Preserve the existing
   secret and passwords when updating an existing service.
5. Apply the reviewed configuration and inspect the build and startup logs.

The Blueprint installs dependencies with `uv sync --frozen --no-dev` and starts
`scripts/start.sh`. Startup prepares the schema explicitly before starting Uvicorn.
Automatic deployment is disabled in the repository configuration. For an existing
service, verify both its deployment setting and the Blueprint Auto Sync setting.

For the public demo, use [render.demo.yaml](render.demo.yaml) and follow
[Demo operations](docs/DEMO_OPERATIONS.md), including the database endpoint guard.

### Manual web service setup

Create a Web Service connected to the repository with these settings:

| Setting | Value |
| --- | --- |
| Branch | `main`, or the explicitly selected release branch |
| Runtime | Python 3 |
| Region | Close to the Neon database |
| Health check | `/health` |
| Automatic deployment | Off; deploy a validated commit manually |

Build command:

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh && export PATH="$HOME/.local/bin:$PATH" && uv sync --frozen --no-dev
```

Start command:

```sh
export PATH="$HOME/.local/bin:$PATH" && sh scripts/start.sh
```

Configure these environment variables:

| Key | Value |
| --- | --- |
| `DATABASE_URL` | Your Neon connection string |
| `ENVIRONMENT` | `production` |
| `DEBUG` | `false` |
| `ADMIN_USER` | `admin` |
| `ADMIN_PASS` | A strong Admin password |
| `CLIENT_USER` | `client` |
| `CLIENT_PASS` | A strong Client password |
| `SESSION_SECRET` | A unique, securely generated session signing secret |
| `DEMO_MODE` | `false` for a regular deployment |

Create the service, then verify the deployed commit and application behavior.
Public `test` passwords are reserved for demo mode; do not use them for private data.

## 3. Deploy on Fly.io

The repository includes [fly.toml](fly.toml) and a [Dockerfile](Dockerfile).
Review the application name and region before creating resources.

1. Install the Fly CLI using the provider's installation instructions.
2. Sign in and initialize the application:

   ```sh
   fly auth login
   fly launch --no-deploy
   ```

3. Configure the following secrets using your own values:

   ```sh
   fly secrets set \
     DATABASE_URL="YOUR_NEON_CONNECTION_STRING" \
     ADMIN_USER="admin" \
     ADMIN_PASS="YOUR_STRONG_ADMIN_PASSWORD" \
     CLIENT_USER="client" \
     CLIENT_PASS="YOUR_STRONG_CLIENT_PASSWORD" \
     SESSION_SECRET="YOUR_UNIQUE_SESSION_SECRET"
   ```

   Replace placeholders securely and avoid retaining secrets in shell history.
   `fly.toml` sets production mode and disables debug output. The container starts
   through `scripts/start.sh`, including schema preparation.

4. Deploy and open the application:

   ```sh
   fly deploy
   fly open
   ```

The native Render deployment is the validated public demo path. Validate the
container build and Fly.io deployment separately before relying on that option.

## 4. Verify a release

- Check `/health` for an `ok` status and the expected deployment commit when available.
- Open `/login?lang=en` and sign in with both roles.
- Verify the dashboard, month navigation, themes, and language selection.
- Open `/docs`; use HTTP Basic credentials for protected API operations.
- Export a monthly PDF and check its totals, dates, and export timestamp.
- Confirm Client cannot perform write operations.
- Inspect startup logs and observe health for at least five minutes.

For existing data, follow the backup, isolated restore, and release procedure in
[Operations](docs/OPERATIONS.md) before deploying application changes.

[Back to technical documentation](docs/README.md)

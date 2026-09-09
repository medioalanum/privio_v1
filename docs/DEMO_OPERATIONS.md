# Operating the public demonstration

## Account boundaries

The company application and public demo use separate Render accounts and separate
Neon accounts. Keep account emails, recovery information and service IDs in a
private operational inventory, not the public README. Use separate browser
profiles. Before changing a resource, verify the signed-in account and service ID.

The company service keeps its existing URL and private credentials. Only the demo
URL and public application credentials belong in the README. Never copy the
company database, backups, environment files or screenshots into the demo.

## Provisioning and releases

`render.yaml` describes the company service with automatic deployment disabled.
The company Blueprint also has Auto Sync disabled in Render; keep both controls
manual so repository edits cannot update the company infrastructure indirectly.
`render.demo.yaml` describes the independently provisioned demo in Frankfurt.
The demo database is a new Neon PostgreSQL 18 project in Frankfurt. DEMO_MODE is
true only on the demo; ENVIRONMENT remains production so cookies use HTTPS.

Both services use the same repository. Run Quality checks first, publish the
selected commit to the demo, test both roles and PDF exports, then publish that
same validated commit to the company service only as a separately planned release.
The company service is not automatically updated by README commits or demo work.
Reverting demo code must not restore or modify the company database.

The public-repository Render connection is initially managed with manual deploys.
Do not assume pushes deploy automatically. Confirm the commit through /health.

## Examples and daily reset

Startup invokes `scripts.demo` only when DEMO_MODE=true. It initializes an empty
allowlisted database once; subsequent restarts preserve visitor edits. The public
Admin can change fictional financial records, but cannot manage Render/Neon or
trigger the reset workflow. Shared edits are visible to other visitors.

The GitHub Actions `Reset public demo` workflow requests a reset daily at 03:17 UTC,
with manual dispatch available to repository maintainers. It uses the `demo`
environment and secret `DEMO_DATABASE_URL`, containing only the demo connection.
Never provide company credentials to this workflow. GitHub schedules are best
effort and may be disabled after 60 days of repository inactivity; inspect the
workflow status and reactivate if needed. A missed reset does not block the app.

The reset verifies DEMO_MODE and the hardcoded demo endpoint before connecting,
requires a bootstrap marker, locks tables against simultaneous edits, deletes and
recreates synthetic examples in one transaction, and preserves ID sequences.
If seeding fails, the transaction rolls back. The endpoint allowlist must be
reviewed explicitly if the demo project is recreated. An unmarked database with
existing records is refused. There is no public HTTP reset endpoint.

## Verification and limits

Run lint, formatting, type checks, Python tests with isolated PostgreSQL and the
JavaScript menu regressions. Test initialization, repeated startup, reset rollback,
Client write denial, Admin edits, languages, themes and monthly PDFs.
After deployment inspect logs, published commit and health for at least five minutes.
Screenshots must contain only the synthetic demo dataset.

Render Free sleeps after inactivity, so initial access may take about a minute.
Avoid keep-alive pings. Check Render and Neon usage alerts in the demo accounts,
review reset failures, and retain recovery methods for both accounts. Company
backups remain independent; demo data is disposable and rebuilt from code.

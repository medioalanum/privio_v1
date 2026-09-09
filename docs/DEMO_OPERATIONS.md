# Operating the public demonstration

## Account boundaries

Only fictional records belong in the public demo. Do not upload real financial
data, backups, private environment files or screenshots containing personal data.
Before changing a resource, verify the signed-in account and selected resource.

## Provisioning and releases

`render.demo.yaml` describes the public demo. Its database uses PostgreSQL 18.
DEMO_MODE is true for the demo; ENVIRONMENT remains production so cookies use HTTPS.

Run Quality checks before publishing a selected commit. Test both roles and PDF
exports after deployment. Review automatic deployment and Blueprint Auto Sync
settings explicitly; do not assume pushes deploy automatically. Confirm the
published commit through /health.

## Examples and daily reset

Startup invokes `scripts.demo` only when DEMO_MODE=true. It initializes an empty
allowlisted database once; subsequent restarts preserve visitor edits. The public
Admin can change fictional financial records, but cannot manage Render/Neon or
trigger the reset workflow. Shared edits are visible to other visitors.

The GitHub Actions `Reset public demo` workflow requests a reset daily at 03:17 UTC,
with manual dispatch available to repository maintainers. It uses the `demo`
environment and secret `DEMO_DATABASE_URL`, containing only the demo connection.
Never provide credentials for a database containing real data to this workflow. GitHub schedules are best
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

Review hosting usage alerts and reset failures, and retain account recovery
methods. Demo data is disposable and rebuilt from code.

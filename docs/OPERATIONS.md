# Operations and preservation

## macOS setup

Keep Python and dependencies isolated: `uv sync --frozen --all-groups --python 3.12`.
Configure `.env` with a development database only. Prepare the schema explicitly
with `uv run python -m scripts.migrate`; start using `sh scripts/start.sh`.
Never point ordinary tests or demo fixtures at production. Tests use SQLite by default. PRIVIO_TEST_DATABASE_URL enables PostgreSQL tests
only for an isolated database whose name starts with privio_test_.
Run `uv run ruff check .`, `uv run ruff format --check .`, `uv run ty check .`,
and `uv run pytest`. CI runs these checks on pushes and PRs.

## Financial definitions

`app/services/decisions.py` supplies the dashboard. All money arithmetic uses
Decimal. The selected month is the due-date month, not payment month. Settlement
is the planned value of settled occurrences; total = settled planned + pending.
Actual realized result is deposits dated in the selected month through today
minus payments by actual payment date in that interval. A discounted settlement
may differ from the planned settled amount; the payment record preserves both.
The existing system settles a bill with one payment, not cumulative partials.

Current balance includes active accounts and their posted movements through today.
Unknown assignment, legacy paid statuses without payment records, allocation-only
accounts, or currencies other than EUR suppress a consolidated projection. No FX
conversion is performed. Commitments have an implicit EUR currency in this stack.
Opening balances must represent balances before the recorded ledger movements;
users must review legacy opening amounts before relying on projections.

Seven days is today through today+6 inclusive, independent of selected month.
Overdue includes all earlier occurrences still pending. Projections start with
current balance and include pending outflows through selected month end; overdue
outflows enter today without rewriting their due dates. Expected income is kept
separate from deposits; overdue expected income is excluded until reviewed.
Receipt links exactly one deposit and stops counting that expectation. No future
record is treated as cash already available. Past months show realized movements;
no reconstructed historical closing balance is asserted.

A legacy estimate flag or ESTIMATIVA description means estimated. False/missing
never implies confirmed. `occurrence_reviews` stores explicit occurrence review.
The annual forecast is a secondary schedule of full obligations, not free cash.

## Schema changes

`python -m scripts.migrate` retains the existing inspector-guarded additive
migration mechanism. It creates missing tables/columns and uses a PostgreSQL
transaction advisory lock to serialize concurrent invocations. It never seeds,
creates payments from statuses, changes dates, rewrites balances, or deletes rows.
New tables: occurrence_reviews, expected_income. Production startup runs this
explicit step before the app. Failures stop startup instead of being swallowed.

## Backup, restore and release gates

Use PostgreSQL 18 pg_dump in custom format over a direct PostgreSQL connection.
Open a REPEATABLE READ READ ONLY transaction, export its snapshot and pass it to
pg_dump while that transaction stays open. Hash each canonical JSON record keyed
in primary-key order from the same snapshot. Store dump, manifest, timestamp and
application commit outside Git with directory mode 0700 and files 0600. Do not
publish row hashes, counts of personal activity, connection strings or raw logs.

Restore with pg_restore --no-owner --no-acl --exit-on-error into a separately named
empty PostgreSQL database. Never restore over the live database. Compare every
record/field, relationships and numeric/date/status values by canonical hashes.
Apply the migration twice and repeat comparisons against all original tables.
New tables are legitimate additions; unexpected original-row changes block release.

Before releasing, complete CI, candidate validation, a restore rehearsal and a
fresh backup. Verify the correct service, branch, DATABASE_URL and start command.
Review automatic deployment and infrastructure synchronization settings before
merging changes. Compare a repeatable-read pre-release snapshot to a post-release
snapshot; distinguish new legitimate writes from loss.
Do not impose destructive rollback or replace the live database with a backup.

Rollback application code only, keeping additive tables. Validate that the
rollback revision preserves explicit migrations and does not synthesize historical
payments or overwrite existing financial records during startup.
Verify health, logs, published SHA, selected months and annual forecast read-only.
Monitor at least five minutes after release; report actual observed duration.

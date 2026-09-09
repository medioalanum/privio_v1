# Admin / Client: incremental releases

## Contract

Admin manages the month; Client views a high-level summary. Both use the same
financial source. Current funds never include expected income. The total through
month end includes overdue bills once. Unknown balances remain unknown.
Preserve the stack, passwords, permissions, IDs, and all records. Presentation
changes must not migrate the database or modify records to produce sample figures.

## Phases and commits

0. Plan and baseline tests, without deployment.
1. Admin/Client labels, admin/client logins, and explicit credential configuration;
   authentication and isolation tests. Deployment 1.
2. Shared financial summary and Admin operations dashboard: three figures,
   overdue bills included, and a simple list; financial and HTTP tests. Deployment 2.
3. Client: monthly coverage, alerts, and collapsed details without write actions;
   permission and chart tests on desktop and mobile. Deployment 3.
4. Cumulative monthly forecast, translations, and visual polish; boundary,
   projection, and regression tests. Deployment 4.

## Release gates

Require CI, the complete test suite, diff review, visual validation with synthetic
data, a fresh backup, and a verified restore into an isolated database. Record the
release revision, per-record checks, and legitimate differences. Complete release
gates before deploying. Roll back compatible application code only; never replace
the database with an old backup. Missing evidence or access blocks deployment.

## Acceptance criteria

Admin can quickly understand what is due, available funds, and any surplus or
shortfall. Client can understand coverage and months with insufficient funds
without managing records. Mobile pages have no horizontal overflow. Status uses
both text and color; actions have labels, keyboard access works, and chart values
are also available as text.

[Back to technical documentation](README.md)

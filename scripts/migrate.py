"""Explicit additive schema migration; never invent or rewrite ledger records."""

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

import app.models  # noqa: F401
from app.database import Base, engine


def migrate(target: Engine) -> None:
    with target.begin() as connection:
        if target.dialect.name == "postgresql":
            connection.execute(text("SELECT pg_advisory_xact_lock(7386202609)"))
        Base.metadata.create_all(connection)
        for table, column, definition in [
            ("occurrence_reviews", "reviewed_amount", "NUMERIC(12,2)"),
            ("commitment_adjustments", "adjusted_date", "DATE"),
            ("deposits", "account_id", "INTEGER REFERENCES financial_accounts(id)"),
            ("payments", "account_id", "INTEGER REFERENCES financial_accounts(id)"),
        ]:
            columns = {c["name"] for c in inspect(connection).get_columns(table)}
            if column not in columns:
                connection.execute(
                    text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
                )


if __name__ == "__main__":
    migrate(engine)
    print("Additive schema preparation complete; ledger records unchanged.")

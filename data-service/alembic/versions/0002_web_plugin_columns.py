"""Web plugin columns: latency, jitter and location provenance

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-09
"""
from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "coverage_measurements"
COLUMNS = [
    sa.Column("latency_ms", sa.Integer()),
    sa.Column("jitter_ms", sa.Integer()),
    sa.Column("location_type", sa.String(10)),  # 'gps' (client) or 'ip' (server-derived)
    sa.Column("location_accuracy", sa.Float()),  # meters
]


def _existing_columns() -> set:
    if context.is_offline_mode():  # no database to inspect when generating SQL
        return set()
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(TABLE)}


def upgrade() -> None:
    existing = _existing_columns()
    for column in COLUMNS:
        if column.name not in existing:
            op.add_column(TABLE, column)


def downgrade() -> None:
    existing = _existing_columns()
    for column in reversed(COLUMNS):
        if column.name in existing:
            op.drop_column(TABLE, column.name)

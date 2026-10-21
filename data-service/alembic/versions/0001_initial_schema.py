"""Initial schema (api_keys and coverage_measurements)

This is the schema as deployed before migrations existed, created by
SQLAlchemy's create_all(). Existing databases already have these tables, so
each one is only created when missing; on those databases this revision is
effectively a no-op that records the baseline in alembic_version.

Revision ID: 0001
Revises:
Create Date: 2026-09-09
"""
from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(name: str) -> bool:
    if context.is_offline_mode():  # no database to inspect when generating SQL
        return False
    return sa.inspect(op.get_bind()).has_table(name)


def upgrade() -> None:
    if not _has_table("api_keys"):
        op.create_table(
            "api_keys",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("phone_identifier", sa.String(), nullable=False),
            sa.Column("api_key", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime()),
        )
        op.create_index("ix_api_keys_id", "api_keys", ["id"])
        op.create_index("ix_api_keys_phone_identifier", "api_keys", ["phone_identifier"], unique=True)
        op.create_index("ix_api_keys_api_key", "api_keys", ["api_key"], unique=True)

    if not _has_table("coverage_measurements"):
        op.create_table(
            "coverage_measurements",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("api_key", sa.String(), nullable=False),
            sa.Column("phone_identifier", sa.String()),
            sa.Column("timestamp", sa.DateTime()),
            sa.Column("latitude", sa.Float()),
            sa.Column("longitude", sa.Float()),
            sa.Column("gps_accuracy", sa.Float()),
            sa.Column("signal_strength_dbm", sa.Integer()),
            sa.Column("signal_strength_asu", sa.Integer()),
            sa.Column("network_type", sa.String()),
            sa.Column("data_network_type", sa.String()),
            sa.Column("mcc", sa.Integer()),
            sa.Column("mnc", sa.Integer()),
            sa.Column("cell_id", sa.BigInteger()),
            sa.Column("app_name", sa.String()),
            sa.Column("app_version", sa.String()),
            sa.Column("library_version", sa.String()),
            sa.Column("download_speed_kbps", sa.Float()),
            sa.Column("upload_speed_kbps", sa.Float()),
        )
        op.create_index("ix_coverage_measurements_id", "coverage_measurements", ["id"])
        op.create_index("ix_coverage_measurements_api_key", "coverage_measurements", ["api_key"])
        op.create_index("ix_coverage_measurements_phone_identifier", "coverage_measurements", ["phone_identifier"])


def downgrade() -> None:
    op.drop_table("coverage_measurements")
    op.drop_table("api_keys")

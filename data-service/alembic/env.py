"""
Alembic environment. Runs migrations against DATABASE_URL, or against the
connection passed in `config.attributes["connection"]` when invoked from
the service at startup (see migrate.py).
"""
import os
import sys
from pathlib import Path

from alembic import context
from sqlalchemy import create_engine

# Make `shared` importable both in the image (/app/shared) and from a checkout
# (<repo>/shared) when running `alembic` from the data-service directory.
_HERE = Path(__file__).resolve().parent
for candidate in (_HERE.parent, _HERE.parent.parent):
    if (candidate / "shared").is_dir() and str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from shared.database.connection import Base  # noqa: E402
from shared.database import models  # noqa: E402,F401  (registers the tables)

config = context.config
target_metadata = Base.metadata


def get_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql://coverage:coverage@postgres:5432/coverage_db")


def run_migrations_offline() -> None:
    """Emit SQL without connecting (alembic upgrade --sql)."""
    context.configure(url=get_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connection = config.attributes.get("connection")
    if connection is not None:
        _run(connection)
        return
    engine = create_engine(get_url())
    with engine.connect() as connection:
        _run(connection)
    engine.dispose()


def _run(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

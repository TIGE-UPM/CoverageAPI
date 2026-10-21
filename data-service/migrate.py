"""
Run the Alembic migrations in ./alembic against the shared database engine.

Called at service startup so that redeploying is enough to migrate; it can
also be run by hand from the data-service directory with `alembic upgrade head`.
"""
import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy.engine import Engine

ALEMBIC_INI = Path(__file__).resolve().parent / "alembic.ini"

logger = logging.getLogger("data-service")


def alembic_config() -> Config:
    return Config(str(ALEMBIC_INI))


def current_revision(engine: Engine):
    with engine.connect() as connection:
        return MigrationContext.configure(connection).get_current_revision()


def head_revision() -> str:
    return ScriptDirectory.from_config(alembic_config()).get_current_head()


def run_migrations(engine: Engine) -> str:
    """Upgrade the database to the latest revision. Returns that revision."""
    before = current_revision(engine)
    config = alembic_config()
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
    after = current_revision(engine)
    if before != after:
        logger.info(f"Database migrated from revision {before or 'none'} to {after}")
    return after

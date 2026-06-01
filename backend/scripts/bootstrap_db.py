"""Container-start database bootstrap — runs before the app, keeps migration files untouched.

The initial migration (0001) builds the FULL current schema via `Base.metadata.create_all`,
while 0002+ are written as incremental `ALTER`s. On a brand-new database that combination
collides: 0001 already created the columns 0002+ try to add ("column already exists"). Rather
than rewrite migration history, we branch on the database's actual state:

  - uninitialized (no alembic_version): run 0001 to build the schema, then STAMP head — on a
    create_all'd database the additive migrations are redundant, so we mark them applied.
  - at 0001 only (e.g. a prior deploy that ran 0001 then failed on 0002): the schema is
    already complete, so just STAMP head to advance the version marker.
  - anything else: a normal `upgrade head` — the path a genuinely incremental future migration
    takes on an already-initialized database.

Run from backend/:  python -m scripts.bootstrap_db
"""

from __future__ import annotations

import logging

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine

from alembic import command
from app.shared.db import sync_database_url

log = logging.getLogger("bootstrap_db")

# The create_all snapshot. A DB sitting exactly here already has the complete current schema,
# so the additive migrations after it are no-ops we can stamp past instead of run.
BASE_REVISION = "0001"


def main() -> None:
    engine = create_engine(sync_database_url())
    try:
        with engine.connect() as conn:
            current = MigrationContext.configure(conn).get_current_revision()
    finally:
        engine.dispose()

    cfg = Config("alembic.ini")
    if current is None:
        log.info("fresh database: building schema at %s, then stamping head", BASE_REVISION)
        command.upgrade(cfg, BASE_REVISION)
        command.stamp(cfg, "head")
    elif current == BASE_REVISION:
        log.info("database at %s (create_all snapshot): stamping head", BASE_REVISION)
        command.stamp(cfg, "head")
    else:
        log.info("database at %s: upgrading to head", current)
        command.upgrade(cfg, "head")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")
    main()

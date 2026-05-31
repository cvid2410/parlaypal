"""Reset cached async clients between tests.

pytest-asyncio runs each test in its own event loop. The module-global async engine and
Redis pool would otherwise carry a connection bound to a closed loop into the next test.
Clearing the caches makes each test build fresh clients on its own loop.
"""

import pytest

import app.services.cache as cache
import app.shared.db as db


@pytest.fixture(autouse=True)
def _reset_async_clients():
    db._engine = None
    db._sessionmaker = None
    cache._pool = None
    yield
    db._engine = None
    db._sessionmaker = None
    cache._pool = None

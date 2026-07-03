import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock

from httpx import AsyncClient, ASGITransport

from dependencies.authorization import require_moderator, group_moderators_id, group_admins_id, require_admin
from dependencies.users import get_current_user_model
from main import app
from db.session_postgresql import get_db


@pytest.fixture
def mock_db():
    session = AsyncMock()
    session.execute = AsyncMock(return_value=MagicMock())
    session.add = MagicMock()
    session.delete = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest_asyncio.fixture
async def client(mock_db):

    async def override_get_db():
        yield mock_db

    def override_require_moderator():
        return MagicMock(id=1, group_id=group_moderators_id)

    def override_require_admin():
        return MagicMock(id=2, group_id=group_admins_id)

    def override_get_current_user_model():
        return MagicMock(id=3)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_moderator] = override_require_moderator
    app.dependency_overrides[require_admin] = override_require_admin
    app.dependency_overrides[get_current_user_model] = override_get_current_user_model

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def anyio_backend():
    return "asyncio"
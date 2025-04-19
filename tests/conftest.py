import pytest

from datetime import datetime, timedelta, timezone

from asgi_lifespan import LifespanManager
from httpx import AsyncClient, ASGITransport

from app.main import app as fastapi_app
from app.internal import constants

from app.internal.database import MainDatabase
from app.internal.config import settings
from app.models.common import SessionInfo


@pytest.fixture(scope='module')
def anyio_backend():
    return 'asyncio'


@pytest.fixture(scope='module')
async def app():
    async with LifespanManager(fastapi_app) as manager:
        yield manager


@pytest.fixture(scope='module')
async def client(app):
    async with AsyncClient(
        transport=ASGITransport(app.app),
        base_url='http://test'
    ) as client:
        yield client


@pytest.fixture(scope='module')
async def database(app) -> MainDatabase:
    return app._state['db']


@pytest.fixture(scope='module')
async def first_user_session(database: MainDatabase):
    expire_offset: timedelta = timedelta(days=30)
    expires_on: datetime = datetime.now(timezone.utc) + expire_offset

    str_date: str = datetime.strftime(expires_on, "%Y-%m-%d %H:%M:%S")
    token = await database.users.create_session(settings.FIRST_USER_NAME, str_date)

    assert token not in [constants.DATE_EXPIRED, constants.NO_USER, constants.INVALID_DATETIME]
    session = await database.users.get_session_info(token)

    session_model = SessionInfo(**session)

    assert session_model.username == settings.FIRST_USER_NAME
    assert session_model.token == token

    assert not session_model.expired
    return session_model

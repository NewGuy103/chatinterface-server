import pytest

from pathlib import Path

from asgi_lifespan import LifespanManager
from httpx import AsyncClient, ASGITransport
from sqlmodel import SQLModel, Session, create_engine, text

from app.main import app as fastapi_app
from app.dependencies import get_session

from app.internal.database import database
from app.internal.config import settings


@pytest.fixture(scope='session')
def anyio_backend():
    return 'asyncio'


@pytest.fixture(scope='session', name='testing_engine')
async def override_database():
    engine = create_engine(
        "sqlite:///testing.db",
        echo=False
    )
    database.override_engine(engine)

    # Tests dont need alembic
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        statement = text("PRAGMA foreign_keys=ON;")
        session.exec(statement)
    
    return engine


@pytest.fixture(scope='session', autouse=True)
async def setup_and_cleanup():
    yield

    test_database = Path('testing.db').resolve()
    test_database.unlink(missing_ok=True)


@pytest.fixture(scope='session')
def session(testing_engine):
    with Session(testing_engine) as session:
        yield session


@pytest.fixture(scope='session')
async def get_lifespan_app(session: Session):
    async def session_override():
        return session

    async with LifespanManager(fastapi_app) as manager:
        fastapi_app.dependency_overrides[get_session] = session_override
        yield manager
    
    fastapi_app.dependency_overrides.clear()


@pytest.fixture(scope='session')
async def client_factory(get_lifespan_app):
    transport = ASGITransport(get_lifespan_app.app)

    async def inner(cookies: dict = None):
        client = AsyncClient(
            transport=transport, base_url='http://test',
            cookies=cookies
        )
        return client
    
    return inner


@pytest.fixture(scope='session')
async def first_user_cookies(client_factory):
    client: AsyncClient = await client_factory()

    auth_data: dict = {
        'grant_type': 'password',
        'username': settings.FIRST_USER_NAME,
        'password': settings.FIRST_USER_PASSWORD
    }
    res = await client.post('/api/token/', data=auth_data)

    assert res.status_code == 200
    assert res.cookies.get('x_auth_cookie')

    await client.aclose()
    return res.cookies

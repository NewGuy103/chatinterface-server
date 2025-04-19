import pytest
from httpx import AsyncClient

from app.models.common import SessionInfo
from app.internal.database import MainDatabase
from app.internal.config import settings

pytestmark = pytest.mark.anyio


async def test_session_token(client: AsyncClient, database: MainDatabase):
    auth_data: dict = {
        'username': settings.FIRST_USER_NAME,
        'password': settings.FIRST_USER_PASSWORD
    }
    res = await client.post('/api/token/', data=auth_data)
    assert res.status_code == 200
    assert res.json() == {'success': True}

    client.cookies.delete('authorization')


async def test_session_token_invalid(client: AsyncClient):
    auth_data: dict = {
        'username': settings.FIRST_USER_NAME,
        'password': "Invalid"
    }
    res = await client.post('/api/token/', data=auth_data)
    assert res.status_code == 401


async def test_check_session_token(client: AsyncClient, first_user_session):
    cookies = {'authorization': first_user_session.token}
    res = await client.get('/api/token/session_info', cookies=cookies)
    assert res.status_code == 200


import pytest
from httpx import AsyncClient

from app.internal.database import MainDatabase
from app.internal.config import settings

pytestmark = pytest.mark.anyio


async def test_session_token(client_factory, first_user_cookies):
    client: AsyncClient = await client_factory(first_user_cookies)
    auth_data: dict = {
        'grant_type': 'password',
        'username': settings.FIRST_USER_NAME,
        'password': settings.FIRST_USER_PASSWORD
    }

    res = await client.post('/api/token/', data=auth_data)

    assert res.status_code == 200
    assert res.json() == {'success': True}

    await client.aclose()


async def test_session_token_invalid(client_factory, first_user_cookies):
    client: AsyncClient = await client_factory(first_user_cookies)

    auth_data: dict = {
        'grant_type': 'password',
        'username': settings.FIRST_USER_NAME,
        'password': "Invalid"
    }
    res = await client.post('/api/token/', data=auth_data)

    assert res.status_code == 401
    await client.aclose()


async def test_check_session_token(client_factory, first_user_cookies):
    client: AsyncClient = await client_factory(first_user_cookies)
    res = await client.get('/api/token/info')

    assert res.status_code == 200
    assert res.json()['username'] == settings.FIRST_USER_NAME
    
    await client.aclose()

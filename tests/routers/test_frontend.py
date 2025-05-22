import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_frontend_redirect_to_login(client_factory):
    client: AsyncClient = await client_factory()
    res = await client.get('/frontend/')

    assert res.status_code == 307
    assert res.headers.get('location') == '/frontend/login'

    await client.aclose()


@pytest.mark.anyio
async def test_frontend_login_redirect_to_main(client_factory, first_user_cookies):
    client: AsyncClient = await client_factory(first_user_cookies)
    res = await client.get('/frontend/login')

    assert res.status_code == 307
    assert res.headers.get('location') == '/frontend/'

    await client.aclose()

import pytest
from httpx import AsyncClient

@pytest.mark.anyio
async def test_main_redirection(client_factory, first_user_cookies):
    client: AsyncClient = await client_factory(first_user_cookies)
    res = await client.get('/')

    assert res.status_code == 307
    assert res.headers.get('location') == '/frontend'

    await client.aclose()

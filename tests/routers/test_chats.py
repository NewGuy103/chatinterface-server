import pytest
import uuid

from httpx import AsyncClient
from sqlmodel import Session
from pydantic import TypeAdapter, ValidationError

from app.models.chats import MessagesGetPublic
from app.internal.config import settings
from app.internal.database import database

# TODO: Add WebSocket stuff to check if its being sent to the sockets
pytestmark = pytest.mark.anyio


async def test_compose_message(client_factory, first_user_cookies, session: Session):
    created = await database.users.add_user(session, 'test_chat_user', 'test_chat_user')
    assert isinstance(created, bool) and created

    client: AsyncClient = await client_factory(first_user_cookies)
    post_data = {'recipient': 'test_chat_user', 'message_data': 'HelloWorld'}

    res = await client.post(
        '/api/chats/message/compose',
        json=post_data
    )
    res_json = res.json()

    ta = TypeAdapter(uuid.UUID)
    assert res.status_code == 200

    try:
        ta.validate_python(res_json)
    except ValidationError as e:
        assert False, str(e.errors())

    await client.aclose()


async def test_compose_message_to_self(client_factory, first_user_cookies):
    client: AsyncClient = await client_factory(first_user_cookies)
    post_data = {'recipient': settings.FIRST_USER_NAME, 'message_data': 'HelloWorld'}

    res = await client.post(
        '/api/chats/message/compose',
        json=post_data
    )
    res_json = res.json()

    assert res.status_code == 400
    assert res_json == {'detail': "Cannot send message to self"}

    await client.aclose()


async def test_compose_message_after_first_compose(client_factory, first_user_cookies):
    client: AsyncClient = await client_factory(first_user_cookies)
    post_data = {'recipient': 'test_chat_user', 'message_data': 'HelloWorldTwo'}

    res = await client.post(
        '/api/chats/message/compose',
        json=post_data
    )

    assert res.status_code == 409
    await client.aclose()


async def test_compose_message_invalid_recipient(client_factory, first_user_cookies):
    client: AsyncClient = await client_factory(first_user_cookies)
    post_data = {'recipient': 'invalid_user', 'message_data': 'HelloWorldTwo'}

    res = await client.post(
        '/api/chats/message/compose',
        json=post_data
    )

    assert res.status_code == 404
    await client.aclose()


async def test_send_message(client_factory, first_user_cookies):
    client: AsyncClient = await client_factory(first_user_cookies)
    post_data = {'recipient': 'test_chat_user', 'message_data': 'HelloWorldAgain'}

    res = await client.post(
        '/api/chats/message',
        json=post_data
    )
    res_json = res.json()

    ta = TypeAdapter(uuid.UUID)
    assert res.status_code == 200

    try:
        ta.validate_python(res_json)
    except ValidationError as e:
        assert False, str(e.errors())

    await client.aclose()


async def test_send_message_to_self(client_factory, first_user_cookies):
    client: AsyncClient = await client_factory(first_user_cookies)
    post_data = {'recipient': settings.FIRST_USER_NAME, 'message_data': 'HelloWorld'}

    res = await client.post(
        '/api/chats/message',
        json=post_data
    )
    res_json = res.json()

    assert res.status_code == 400
    assert res_json == {'detail': "Cannot send message to self"}

    await client.aclose()


async def test_send_message_without_relation(client_factory, first_user_cookies, session: Session):
    created = await database.users.add_user(session, 'test_chat_user2', 'test_chat_user2')
    assert isinstance(created, bool) and created

    client: AsyncClient = await client_factory(first_user_cookies)
    post_data = {'recipient': 'test_chat_user2', 'message_data': 'HelloWorld'}

    res = await client.post(
        '/api/chats/message',
        json=post_data
    )
    assert res.status_code == 409

    await client.aclose()


async def test_send_message_invalid_recipient(client_factory, first_user_cookies):
    client: AsyncClient = await client_factory(first_user_cookies)
    post_data = {'recipient': 'invalid_user', 'message_data': 'HelloWorldTwo'}

    res = await client.post(
        '/api/chats/message',
        json=post_data
    )

    assert res.status_code == 404
    await client.aclose()


async def test_get_recipients(client_factory, first_user_cookies):
    client: AsyncClient = await client_factory(first_user_cookies)

    res = await client.get('/api/chats/recipients')
    res_json: list[str] = res.json()

    assert res.status_code == 200
    assert 'test_chat_user' in res_json

    await client.aclose()


async def test_get_previous_messages(client_factory, first_user_cookies):
    client: AsyncClient = await client_factory(first_user_cookies)
    params = {'recipient': 'test_chat_user', 'amount': 100, 'offset': 0}

    res = await client.get('/api/chats/messages', params=params)
    res_json: list[str] = res.json()

    ta = TypeAdapter(list[MessagesGetPublic])
    assert res.status_code == 200

    try:
        ta.validate_python(res_json)
    except ValidationError as e:
        assert False, str(e.errors())

    await client.aclose()


async def test_get_one_latest_message(client_factory, first_user_cookies):
    client: AsyncClient = await client_factory(first_user_cookies)
    params = {'recipient': 'test_chat_user', 'amount': 1, 'offset': 0}

    res = await client.get('/api/chats/messages', params=params)
    res_json: list[str] = res.json()

    ta = TypeAdapter(list[MessagesGetPublic])
    assert res.status_code == 200

    try:
        models = ta.validate_python(res_json)
    except ValidationError as e:
        assert False, str(e.errors())

    model = models[0]

    assert model.message_data == 'HelloWorldAgain'
    assert model.sender_name == settings.FIRST_USER_NAME

    await client.aclose()


async def test_get_one_latest_message_with_one_offset(client_factory, first_user_cookies):
    client: AsyncClient = await client_factory(first_user_cookies)
    params = {'recipient': 'test_chat_user', 'amount': 1, 'offset': 1}

    res = await client.get('/api/chats/messages', params=params)
    res_json: list[str] = res.json()

    ta = TypeAdapter(list[MessagesGetPublic])
    assert res.status_code == 200

    try:
        models = ta.validate_python(res_json)
    except ValidationError as e:
        assert False, str(e.errors())

    model = models[0]
    
    assert model.message_data == 'HelloWorld'
    assert model.sender_name == settings.FIRST_USER_NAME

    await client.aclose()


async def test_get_previous_messages_invalid_user(client_factory, first_user_cookies):
    client: AsyncClient = await client_factory(first_user_cookies)
    params = {'recipient': 'invalid_user', 'amount': 100, 'offset': 0}

    res = await client.get('/api/chats/messages', params=params)

    assert res.status_code == 404
    await client.aclose()


async def test_get_message_using_uuid(client_factory, first_user_cookies):
    client: AsyncClient = await client_factory(first_user_cookies)
    params = {'recipient': 'test_chat_user', 'amount': 100, 'offset': 0}

    res = await client.get('/api/chats/messages', params=params)
    res_json: list[str] = res.json()

    ta = TypeAdapter(list[MessagesGetPublic])
    assert res.status_code == 200

    try:
        models = ta.validate_python(res_json)
    except ValidationError as e:
        assert False, str(e.errors())

    latest_message = models[0]
    res2 = await client.get(f'/api/chats/message/{latest_message.message_id}')

    assert res2.status_code == 200
    res2_json = res2.json()
    try:
        returned_model = MessagesGetPublic(**res2_json)
    except ValidationError as e:
        assert False, str(e.errors())
    
    assert returned_model == latest_message
    await client.aclose()


async def test_get_message_using_invalid_message_id(client_factory, first_user_cookies):
    client: AsyncClient = await client_factory(first_user_cookies)

    random_uuid = str(uuid.uuid4())
    res = await client.get(f'/api/chats/message/{random_uuid}')

    assert res.status_code == 404
    await client.aclose()


async def test_delete_latest_message_using_uuid(client_factory, first_user_cookies):
    client: AsyncClient = await client_factory(first_user_cookies)
    params = {'recipient': 'test_chat_user', 'amount': 100, 'offset': 0}

    res = await client.get('/api/chats/messages', params=params)
    res_json: list[str] = res.json()

    ta = TypeAdapter(list[MessagesGetPublic])
    assert res.status_code == 200

    try:
        models = ta.validate_python(res_json)
    except ValidationError as e:
        assert False, str(e.errors())

    latest_message = models[0]
    res2 = await client.delete(f'/api/chats/message/{latest_message.message_id}')

    assert res2.status_code == 200
    res2_json = res2.json()

    assert res2_json == {'success': True}

    # Check if it doesnt show up in database
    res3 = await client.get(f'/api/chats/message/{latest_message.message_id}')
    assert res3.status_code == 404

    await client.aclose()


async def test_delete_message_using_invalid_message_id(client_factory, first_user_cookies):
    client: AsyncClient = await client_factory(first_user_cookies)

    random_uuid = str(uuid.uuid4())
    res = await client.delete(f'/api/chats/message/{random_uuid}')

    assert res.status_code == 404
    await client.aclose()


async def test_edit_latest_message_using_uuid(client_factory, first_user_cookies):
    client: AsyncClient = await client_factory(first_user_cookies)

    # Make a message
    post_data = {'recipient': 'test_chat_user', 'message_data': 'HelloWorldAgainTwo'}

    res = await client.post(
        '/api/chats/message',
        json=post_data
    )
    res_json = res.json()

    ta = TypeAdapter(uuid.UUID)
    assert res.status_code == 200

    try:
        message_id = ta.validate_python(res_json)
    except ValidationError as e:
        assert False, str(e.errors())

    # Edit the message
    patch_data = {'message_data': "EditedHelloWorld"}
    res2 = await client.patch(f'/api/chats/message/{message_id}', json=patch_data)

    assert res2.status_code == 200
    res2_json = res2.json()

    assert res2_json == {'success': True}

    # And get it after editing
    res3 = await client.get(f'/api/chats/message/{message_id}')

    assert res3.status_code == 200
    res3_json = res3.json()
    try:
        returned_model = MessagesGetPublic(**res3_json)
    except ValidationError as e:
        assert False, str(e.errors())
    
    assert returned_model.message_data == "EditedHelloWorld"
    await client.aclose()


async def test_edit_latest_message_using_invalid_message_id(client_factory, first_user_cookies):
    client: AsyncClient = await client_factory(first_user_cookies)

    random_uuid = str(uuid.uuid4())
    patch_data = {'message_data': "Something"}
    
    res = await client.patch(f'/api/chats/message/{random_uuid}', json=patch_data)

    assert res.status_code == 404
    await client.aclose()

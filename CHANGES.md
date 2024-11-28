# Add HTML frontend and multiple new features

**Version**: v0.1.0

**Date:** 28/11/2024

## Additions

**`main.py`**:

* Added templating for HTML frontend.
* Added static files route under `/static`.
* Added title, version and license info to FastAPI metadata.
* Added an API router to prefix all API routes with `/api`.
* Add root path `/` which redirects to `/frontend/`

**`dependencies.py`**:

* Created `login_required()` dependency used by `/frontend/` to redirect to a login page if no credentials were found.

**`internal/database.by`**:

* Create index `idx_messages_message_id` which indexes message IDs.

**`models/chats.py`**:

* Create `SendMessage`, `EditMessage` and `DeleteMessage` pydantic models.

**`routers/chats.py`**:

* Create `/send_message` route to replace Websocket message sending, and returns a message ID.
* Create `/get_message/{message_id}` to get an message with a specific message ID.
* Create `/edit_message/{message_id}` and `/delete_message/{message_id}` (unfinished).

**`routers/frontend.py`**:

* Create `/frontend/` and `/frontend/login` to serve HTML files.

## Changes

**`main.py`**:

* Changed app lifespan state to use a plain dictionary.

**`OPEN_SOURCE_LICENSES.md`**:

* Removed `msgpack` attribution as it is no longer a dependency.

**`requirements.in | requirements.txt`**:

* Removed `msgpack` as a dependency.

**`dependencies.py`**:

* Changed `get_session_info()` to require a cookie instead of a header.

**`internal/database.by`**:

* Changed return values to use constants instead.

**`models/common.py`**:

* Change `AppState` from a pydantic model to a `NamedTuple` for type hinting.

**`routers/auth.py`**:

* Change `retrieve_token()` to `cookie_login()` and sets a cookie instead of directly giving the token.

**`routers/chats.py`**:

* Change `retrieve_token()` to `cookie_login()` and sets a cookie instead of directly giving the token.

**`routers/ws.py`**:

* Changed authentication to use the `get_session_info_ws()` dependency instead of having it
  send the session token in the first message.
* Websocket now sends data as JSON.
* Disabled receiving messages, will now close the connection if messages are sent to it.
* Removed the ability to send chat messages in Websocket.

**`docker/Dockerfile`**:

* Now copies `/static` and `/templates` to `/app`.

## Misc

* Most routers that check for a constant string now use the `constants` submodule in the app.

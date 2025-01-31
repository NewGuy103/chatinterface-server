# Create websocket clients abstractions and improve logs

**Version**: v0.1.0

**Date:** 31/01/2025

## Additions

**`/README.md`**:

* Added text and link to the MariaDB Python connector.

**`internal/ws.py`**:

* Create module to put `WebsocketClients` abstraction to prevent any unexpected behavior.

**`docker/docker-compose.yml`**:

* Create compose file.

**`internal/constants.py`**:

* Create `WebsocketMessages` enum for websocket message constants.

## Changes

**`/main.py`**:

* Add error check if database cannot connect and log a message accordingly.

**`models/common.py`**:

* Now uses `typing.TYPE_CHECKING` to import the classes.

**`models/dbtables.py`**:

* Default datetimes now use `default_factory` instead of `default` for the current datetime.

**`models/ws.py`**:

* Removed `ClientInfo` as it is now useless.

**`routers/auth.py`**:

* `cookie_login` (or `/`) now returns a `success: true` dictionary instead of a simple bool.
* `/revoke` has been renamed to `/revoke_session` and now properly revokes active WebSocket sessions.
* `/info` has been renamed to `/session_info`.

**`routers/chats.py`**:

* Removed temporary fix and implemented the `WebsocketClients` class for broadcasting the message.
* `/edit_message/{message_id}` and `/delete_message/{message_id}` now returns a `success: true` instead of a simple bool.

**`routers/ws.py`**:

* Replaced `ClientInfo` setup with the `WebsocketClients` class.

## Misc

* Frontend JavaScript has been updated to use the previous commits.

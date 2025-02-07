# Implement message update and delete

**Version**: v0.1.0

**Date:** 07/02/2025

## Additions

**`internal/constants.py`**:

* Create `MESSAGE_UPDATE` and `MESSAGE_DELETE` constants.

**`/main.py`**:

* Added check to enable/disable debug mode.

**`models/dbtables.py`**:

* Added `UserInstance` data model to use `Users` outside of the database session.

**`pyproject.toml`**:

* Created `pyproject.toml` to manage package metadata.

**`internal/config.py`**:

* Added `ENVIRONMENT` env variable to settings.

**`internal/database.py`**:

* Added logging to output any errors that happen during database queries.
* Created `ChatMethods.has_chat_relation` to check if two users have chatted before.

**`docker/docker-compose.yml`**:

* Now uses the GitHub container registry image by default.

## Changes

**`setup.py`**:

* Removed most package metadata and put into `pyproject.toml` instead.

**`internal/config.py`**:

* Removed `DEFAULT_MAIN_CONFIG` as it was not being used.
* Changed `DEFAULT_APP_DIR` from `/opt/chatinterface-server` to `./chatinterface-server_config`.

**`internal/database.py`**:

* `ChatMethods.store_message` now returns a raw UUID instance.
* `ChatMethods.edit_message` and `ChatMethods.delete_message` now returns a `UserInstance`.

**`internal/ws.py`**:

* Logs now use `logger` instead of `logging`.

**`models/ws.py`**:

* Created `MessageUpdate`, `MessageDelete` models to validate data before sending to clients.

**`models/chats.py`**:

* `MessagesGetPublic` now has a `recipient_name` field and uses type aliases.

**`routers/chats.py`**:

* `/send_message` now prevents sending a message if recipient is the same as the session username, and now uses `has_chat_relation` to check chat relation.
* `/edit_message/{message_id}` and `/delete_message/{message_id}` now broadcasts the message to Websocket clients properly.

## Misc

* Frontend JavaScript has been updated to allow message update and delete.
* Message compose has not yet been implemented.

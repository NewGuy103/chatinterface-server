# Fully replace mysql-connector-python with SQLModel ORM

**Version**: v0.1.0

**Date:** 28/01/2025

## Additions

**`models/chats.py`**:

* Added `min_length=1` to `message_data` fields.
* Created `MessagesGetPublic` as the return model for the messages returned form the database.

**`models/dbtables.py`**:

* Added `min_length=1` to `Messages.message_data` field.
* Created `UserChatRelations` table to replace the old method of checking for a chat relation.

**`internal/database.py`**:

* Added check to `ChatMethods.store_message` to prevent empty message data.

## Changes

**`/__init__.py`**:

* Revert not importing submodules, it broke the app.

**`models/chats.py`**:

* Changed `DeleteMessage.message_id` to a UUID type.

**`internal/constants.py`**:

* Removed `ID_MISMATCH` constant, as it is no longer needed.

**`internal/database.py`**:

* `MainDatabase.get_userid` now returns a UUID type or `None` instead of a string.
* Renamed `ChatMethods.get_previous_chats` to `get_chat_relations` and rewritten the function to use `UserChatRelations` instead.
* `ChatMethods.get_messages` and `get_message` rewritten to use SQLModel while the raw SQL is left as a comment.

**`routers/chats.py`**:

* `/recipients` has been changed to `/retrieve_recipients`, and the function name is now `get_chat_relations`.
* `/messages` has been changed to `/retrieve_messages`, and the route now returns a list of `MessagesGetPublic` models.
* `/send_message` and `/compose_message` now returns a UUID.
* `/get_message/{message_id}` now returns a `MessagesGetPublic` model.
* `/delete_message/{message_id}` and `/edit_message/{message_id}` now returns `True`.
* Improved the log message a little.

## Misc

* The frontend will be updated sooner or later to use these recent changes.

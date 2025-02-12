# Create /api/users for user management

**Version**: v0.1.0

**Date:** 12/02/2025

## Additions

**`/main.py`**:

* Added the users router to the main app.

**`internal/database.py`**:

* Created `delete_user` and `get_users` in `UserMethods` for user management.

**`internal/ws.py`**:

* Created `disconnect_all_clients` which disconnects all clients by username.

**`models/users.py`**:

* Created for the `/users` router.

**`routers/users.py`**:

* Created `/users` endpoint for user management.

**`docker/docker-compoose.yml`**:

* Created volume mount which links `./chatinterface_server` to `/app/chatinterface-server_config`.

## Changes

**`routers/chats.py`**:

* Changed `/compose_message` to mimic `/send_message` but for composing.

**`internal/config.py`**:

* Rewrote the logging setup, now only uses `chatinterface_logger` and rewrote `ConfigManager` to only handle the logging configuration.

**`internal/database.py`**:

* Changed `UserMethods.add_user` to return True when successful.

**`models/ws.py`**:

* Moved `UsernameField` to `models/common.py`.

**`docker/Dockerfile`**:

* Changed entrypoint from `uvicorn chatinterface_server.main:app` to `fastapi run chatinterface_server/main.py`.

## Misc

* Frontend JavaScript now shows a message if you are logged out.
* Will create a user management page soon.

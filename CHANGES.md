# Major changes to API and project structure

**Version**: v0.2.0

**Date:** 19/04/2025

## Additions

**`/migrations | /alembic.ini`**:

* Added alembic migrations for both 0.1.0 and 0.2.0.

**`/.python-version`**:

* Added Python version pin.

**`/uv.lock`**:

* Added lockfile to manage project dependencies using `uv`.

**`/pyproject.toml | /OPEN_SOURCE_LICENSES.md`**:

* Added alembic as a dependency.
* Added grip as a dev dependency.

**`/scripts`**:

* Added scripts for alembic.

**`/app/dependencies.py`**:

* Added `get_session` dependency to get an SQLAlchemy database session for each request.

**`/app/main.py`**:

* Added `database.close()` call to app lifespan when stopping the app.

## Changes

**`/MANIFEST.in | /setup.py`**:

* Deleted build related files (uv handles building way better).

**`/requirements.in | /requirements.txt`**:

* Deleted requirements file in favor of `uv.lock` and `pyproject.toml`.

**`/app/internal/database.py`**:

* Internal changes:
  * SQLAlchemy engine is now defined in this module instead of `main.py`.
  * Removed `self.__closed` variable when using `.close()`.
  * No longer creates the database schema using SQLModel, but instead lets alembic handle it.
  * Replaced `MainDatabase.get_userid` with `MainDatabase.get_user` to return the full user model instead.
  * Changed all methods that use `constants` to use the `DBReturnCodes` enum instead.
  * Most methods now throw a ValueError indicating invalid state insetad of returning a constant.
* Method changes:
  * Added `session` parameter to all methods to take in the session from the request as a dependency.
  * Fixed logic error in `UserMethods.check_session_validity()` when checking if date is expired.
  * `ChatMethods.get_chat_relations()` now uses the sender and recipient user models instead of `UserChatRelations`.
  * `ChatMethods.has_chat_relations()` now also uses the sender and recipient models.
  * `ChatMethods.store_message()` no longer uses `UserChatRelations`.

**`/app/dependencies.py`**:

* Changed from a simple `authorization` cookie to an `x_auth_cookie` cookie using `APIKeyCookie`.

**`/app/main.py`**:

* No longer initializes the database in app lifespan, but only calls `setup()`.
* Now logs the current chatinterface-server version on startup.

**`/app/version.py`**:

* Updated version to 0.2.0.

**`/app/internal/config.py`**:

* Added `env_file='.env'` to pydantic settings config.
* Now checks for the default value and raises an error if it's still default in non-local environments.
* `MARIADB_PASSWORD` now has default value of 'helloworld'.
* `STATIC_DIR` and `TEMPLATES_DIR` are now DirectoryPath fields.

**`/app/internal/constants.py`**:

* Moved all top-level constants into a `DBReturnCodes` string enum.

**`/app/models/chats.py`**:

* Removed `DeleteMessage` model due to HTTP DELETE not allowing a request body.

**`/app/models/common.py`**:

* Renamed `SessionInfo` to `UserInfo` to differentiate from SQLAlchemy sessions.
* Removed `db` from `AppState`.

**`/app/models/dbtables.py`**:

* Properly added relationships linking to the `Users` table.
* Removed `UserChatRelations` because relationship models make it way simpler.
* Removed `UserInstance` model.

**`/app/routers/auth.py`**:

* Changed all route names to be more REST-like.
* `POST /api/auth/` now uses a `OAuth2PasswordRequestFormStrict`.

**`/app/routers/chats.py`**:

* Changed all route names to be REST-like.
* `DELETE/PATCH /api/chats/message/{message_id}` now uses the `Users` model directly instead of `UserInstance`.

**`/app/routers/users.py`**:

* Changed all route names to be REST-like.

**`/app/routers/ws.py`**:

* Increased timeout for message to be 45 seconds.
* Now properly catches `asyncio.TimeoutError`.

**`/docker/Dockerfile`**:

* Replaced `pip` with `uv` when building the image.
* Removed leftover `MKDIR /opt/chatinterface-server` instruction.

**`/docker/docker-compose.yml`**:

* Made `MARIADB_PASSWORD` have default value of 'helloworld'.
* `chatinterface_server` now uses the GitHub container registry image by default.

## Misc

* Updated project to have a similar structure to the other syncserver project for consistency.
* Updated frontend JavaScript to reflect the API changes.
* The overall goal is to turn this app and syncserver into a full microservice setup once both
  apps are stable enough.

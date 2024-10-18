# Replace models.py with models/ directory

**Version**: v0.1.0

**Date:** 18/10/2024

## Additions

**`.dockerignore`**:

* Created `.dockerignore` file.

**`docker/Dockerfile`**:

* Created Dockerfile for containerization.

**`models/`**:

* Created `models/` subdirectory to store pydantic models in an organized way.

**`routers/chats.py`**:

* Added `/chats/compose_message` route to replace the implicit message compose happening in the WebSocket connection.

**`main.py`**:

* Added logging.

## Changes

**`models.py`**:

* Deleted `models.py` in favor of `models/` subdirectory.

**`internal/config.py`**:

* Removed `ConfigMaker.create_database_config()` and `ConfigManager.get_database_config()` as
  database is now configured through environment variables.
* `ConfigMaker.create_logging_config()` now enables console logging by default.
* Changed `ConfigManager` to create the directory if it doesn't exist instead of raising an error.

**`internal/database.py`**:

* Changed `MainDatabase` to take in the configuration directly instead of taking in a dictionary
  for both database and executor config.
* Max thread pool workers is now equal to the pool size of the database.

**`routers/ws.py`**:

* Changed `/ws/chat` `message.send` message to return an error if attempting to
  send a chat to a recipient without first composing a message.

**`main.py`**:

* `load_database()` now gets the database credentials from environment variables.

## Misc

* Replaced all imports of `models.py` to import the `models/` subdirectory.

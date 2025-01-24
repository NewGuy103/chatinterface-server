# Progress on replacing mysql-connector-python with sqlmodel

**Version**: v0.1.0

**Date:** 24/01/2025

## Additions

**`setup.py`**:

* Copy requirements from requirements.in to install_requires.

**`dependencies.py`**:

* Added simple `HttpAuthDep` and `SessionOrRedirectDep` type annotation aliases.

**`OPEN_SOURCE_LICENSES.md`**:

* Added `sqlmodel` and `mariadb` attributions.

**`requirements.in | requirements.txt`**:

* Added `sqlmodel` and `mariadb` as dependencies.

**`models/dbtables.py`**:

* Migrated raw SQL tables to SQLModel tables.

**`LICENSES/lgpl-2.1-or-later.txt`**:

* Added license text for `mariadb`.

**`internal/config.py`**:

* Added `AppSettings` which takes configuration from the

## Changes

**`LICENSE``**:

* Relicensed from GPL v2.0 to MPL 2.0.

**`main.py`**:

* Removed `load_database()`, now creates the SQLAlchemy engine directly and passes it to the database.

**`OPEN_SOURCE_LICENSES.md`**:

* Removed `mysql-connector-python` attribution as it is no longer a dependency.

**`requirements.in | requirements.txt`**:

* Removed `mysql-connector-python` as a dependency.

**`internal/database.by`**:

* Changed `MainDatabase` to take an engine as a parameter instead of the database configuration.
* Rewrote `UserMethods` to use SQLModel methods instead of raw SQL.
* Removed `transaction()` context manager, replaced by SQLModel's sessions.

**`routers/auth.py`**:

* Removed existing WebSocket disconnect setup to rework it.

**`models/ws.py`**:

* Removed `ChatMessageSend` model.

**`LICENSES/`**:

* Removed Apache 2.0, BSD 2 and 3 clause, and GPL 2.0 license text.

## Misc

* `__init__.py` files no longer import their submodules to prevent circular imports.
* Migrating from raw SQL to SQLModel not yet complete, only completed migration is `UserMethods`.

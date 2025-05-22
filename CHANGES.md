# Add proper test cases

**Version**: v0.2.0

**Date:** 22/05/2025

## Additions

**`/.github/workflows/tests.yml`**:

* Added pytest action.

**`/pyproject.toml`**:

* Added `pytest-md` and `pytest-emoji` as dev dependencies.

**`/tests/routers/test_chats.py`**:

* Added tests to the chats router.

**`/tests/routers/test_frontend.py`**:

* Added tests to frontend redirection.

**`/tests/conftest.py`**:

* Added fixtures to setup and cleanup tests, override dependencies and engine.

**`/app/internal/database.py`**:

* Added `override_engine()` to `MainDatabase` to allow overriding engine before setup.
* Added `offset=0` parameter to `ChatMethods.get_messages()`

## Changes

**`/app/internal/database.py`**:

* Fixed a bug where `UserMethods.create_session()` used the string representation
  instead of the datetime object.

**`/app/routers/chats.py`**:

* `/api/chats/messages` now has `amount` use PositiveInt and `offset` use NonNegativeInt types.

## Misc

* This commit will be the v0.2.0 release.

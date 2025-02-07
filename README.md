# newguy103-chatInterface-server

A server to create a centralized chat platform, and designed to be self-hosted.

Currently in development, anything can change at any time!

## Requirements

Python 3.10+

## Installation

This application requires the MariaDB Python connector, which depends on the MariaDB C connector. You can find
instructions to install it here: [MariaDB Python Connector](https://mariadb.com/docs/server/connect/programming-languages/python/install/).

`pip install newguy103-chatinterface-server` (Note: Not yet fully ready on PyPI)

This will install the necessary dependencies, and the app itself as `chatinterface_server`.

If you want to clone the repository directly:

```bash
git clone https://github.com/newguy103/chatinterface-server
cd chatinterface-server
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

There is also a container image published on the GitHub container registry if you use Docker or other containerization platforms.

## Usage

To run the application:

`uvicorn chatinterface_server.main:app`

This will also work for the cloned environment, but you must execute this in the cloned environment's directory.

You can also pass command-line arguments to `uvicorn`.

If you cloned the repository directly, you can also use the `fastapi` command to run the application.

## Disclaimer

This project is licensed under the Mozilla Public License 2.0.

Open source license attributions can be found in [OPEN_SOURCE_LICENSES.md](OPEN_SOURCE_LICENSES.md)

## Version

0.1.0

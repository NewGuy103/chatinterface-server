# newguy103-chatInterface-server

A server to create a centralized chat platform, and designed to be self-hosted.

Currently in development, anything can change at any time!

## Requirements

* Python 3.11+ and [uv](https://docs.astral.sh/uv/).
* A MariaDB instance.

## Installation

This application requires the MariaDB Python connector, which depends on the MariaDB C connector. You can find
instructions to install it here: [MariaDB Python Connector](https://mariadb.com/docs/server/connect/programming-languages/python/install/).

You can pull the official Docker image using:

```bash
docker pull ghcr.io/newguy103/chatinterface-server:latest
```

If you want to clone the repository directly:

```bash
git clone https://github.com/newguy103/chatinterface-server
cd chatinterface-server
uv sync
```

This will clone the repository and setup the environment.

## Usage

To run the application if you cloned it locally:

```bash
fastapi run app/main.py
```

There is an example Docker Compose file in the [docker](docker/) directory if you
prefer using Docker.

## Disclaimer

This project is licensed under the Mozilla Public License 2.0.

Open source license attributions can be found in [OPEN_SOURCE_LICENSES.md](OPEN_SOURCE_LICENSES.md)

## Version

0.2.0

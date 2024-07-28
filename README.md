# newguy103-chatInterface-server

A server to create a centralized chat platform, and designed to be self-hosted.

Currently a work in progress.

## Requirements

Python 3.10+

## Installation

`pip install newguy103-chatinterface-server`

This will install the necessary dependencies, and the app itself as `chatinterface_server`.

If you want to clone the repository directly:

```bash
git clone https://github.com/newguy103/chatinterface-server
cd chatinterface-server
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

The environment variable `CHATINTERFACE_BASEDIR` must be set to a valid directory, this is
where configuration files and logs will be stored.

To run the application:

`uvicorn chatinterface_server:app`

This will also work for the cloned environment, but you must execute this
in the cloned environment's directory.

You can also pass command-line arguments to `uvicorn`.

## Disclaimer

This project uses the MySQL Python Connector, which is licensed under the GPLv2.0, you can
find the source code [here](https://github.com/mysql/mysql-connector-python).

Open source license attributions can be found in [OPEN_SOURCE_LICENSES.md](OPEN_SOURCE_LICENSES.md)

This project is licensed under the GPLv2.0, as per license terms.
For more details, you can refer to the [GNU General Public License v2.0](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html).

## Version

0.1.0

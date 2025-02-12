import os
import json
import logging.config

from typing import Literal

from pydantic import computed_field, MariaDBDsn
from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

from ..version import __version__

APP_NAME: str = "chatinterface-server"
DEFAULT_APP_DIR: str = os.path.join(".", f"{APP_NAME}_config")


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict()

    ENVIRONMENT: Literal['local', 'development', 'production'] = 'local'
    MARIADB_HOST: str = '127.0.0.1'
    MARIADB_PORT: int = 3306

    MARIADB_DBNAME: str = 'chatinterface_server'
    MARIADB_USER: str = 'chatinterface_server'

    MARIADB_PASSWORD: str = ''

    @computed_field
    @property
    def SQLALCHEMY_ENGINE_URI(self) -> MariaDBDsn:
        return MultiHostUrl.build(
            scheme='mariadb+mariadbconnector',
            username=self.MARIADB_USER,
            password=self.MARIADB_PASSWORD,
            host=self.MARIADB_HOST,
            port=self.MARIADB_PORT,
            path=self.MARIADB_DBNAME
        )

    STATIC_DIR: str = './static'
    TEMPLATES_DIR: str = './templates'

    FIRST_USER_NAME: str = 'admin'
    FIRST_USER_PASSWORD: str = 'helloworld'


def load_or_create_config(config_path: str, default_config: dict) -> dict:
    if not os.path.isfile(config_path):
        with open(config_path, 'w') as file:
            json.dump(default_config, file, indent=4)

        return default_config
    else:
        with open(config_path, 'r') as file:
            return json.load(file)


class ConfigManager:
    def __init__(self, base_dir: str = DEFAULT_APP_DIR) -> None:
        if not base_dir:
            raise ValueError("application base directory required but is empty")
        if not os.path.isdir(base_dir):
            os.makedirs(base_dir, mode=0o755)

        # if two instances are being ran, version separates instances if base dir is same
        abs_base_dir: str = os.path.abspath(base_dir)
        self.base_dir: str = os.path.join(abs_base_dir, __version__)

        os.makedirs(self.base_dir, mode=0o700, exist_ok=True)

    def make_logging_config(self):
        return {
            'version': 1,
            'formatters': {
                'default': {
                    'format': '[%(name)s]: [%(module)s | %(funcName)s] - [%(asctime)s] - [%(levelname)s] - %(message)s',
                    'datefmt': '%Y-%m-%d %H:%M:%S'
                },
                'precise': {
                    'format': (
                        '[%(name)s]: [%(module)s | %(funcName)s] - [%(levelname)s] - "%(pathname)s:%(lineno)d"'
                        ' - [%(asctime)s]: %(message)s'
                    ),
                    'datefmt': '%Y-%m-%d %H:%M:%S'
                }
            },
            'handlers': {
                'console': {
                    'class': 'logging.StreamHandler',
                    'stream': 'ext://sys.stdout',
                    'formatter': 'default'
                },
                "chatinterface_server": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "formatter": "default",
                    "maxBytes": 5 * 1024 * 1024,  # 5 MB
                    "backupCount": 3,
                    "filename": os.path.join(self.base_dir, 'chatinterface_server.log')
                }
            },
            'loggers': {
                "chatinterface_server": {
                    "handlers": [
                        "chatinterface_server",
                        "console"
                    ],
                    "level": "INFO",
                    "propagate": True
                }
            }
        }

    def setup_logging(self) -> None:
        log_config_file: str = os.path.join(self.base_dir, 'logging.json')

        log_config: dict = load_or_create_config(log_config_file, self.make_logging_config())
        logging.config.dictConfig(log_config)


settings: AppSettings = AppSettings()

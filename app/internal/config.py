import os
import json
import logging.config
import warnings

from typing import Literal
from pathlib import Path

from pydantic import computed_field, MariaDBDsn, DirectoryPath, model_validator
from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

from typing import Self
from ..version import __version__

APP_NAME: str = "chatinterface-server"
DEFAULT_APP_DIR: str = os.path.join(".", f"{APP_NAME}_config")


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env', 
        env_file_encoding='utf-8'
    )

    ENVIRONMENT: Literal['local', 'development', 'production'] = 'local'
    MARIADB_HOST: str = '127.0.0.1'
    MARIADB_PORT: int = 3306

    MARIADB_DBNAME: str = 'chatinterface_server'
    MARIADB_USER: str = 'chatinterface_server'

    MARIADB_PASSWORD: str = 'helloworld'

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

    STATIC_DIR: DirectoryPath = Path('./static').resolve()
    TEMPLATES_DIR: DirectoryPath = Path('./templates').resolve()

    FIRST_USER_NAME: str = 'admin'
    FIRST_USER_PASSWORD: str = 'helloworld'


    def _check_value_default(self, key_name: str, value: str):
        if value == 'helloworld':
            msg = (f"The value of '{key_name}' is the default 'helloworld', "
                    "changing it to a different value is recommended.")

            if self.ENVIRONMENT == 'local':
                warnings.warn(msg, stacklevel=1)
            else:
                raise ValueError(msg)

    @model_validator(mode="after")
    def _check_values_okay(self) -> Self:
        self._check_value_default('MARIADB_PASSWORD', self.MARIADB_PASSWORD)
        self._check_value_default('FIRST_USER_PASSWORD', self.FIRST_USER_PASSWORD)

        return self


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
            },
            'disable_existing_loggers': False
        }

    def setup_logging(self) -> None:
        log_config_file: str = os.path.join(self.base_dir, 'logging.json')

        log_config: dict = load_or_create_config(log_config_file, self.make_logging_config())
        logging.config.dictConfig(log_config)


settings: AppSettings = AppSettings()

import os
import json
import logging.config

from pydantic import computed_field, MariaDBDsn
from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings, SettingsConfigDict
from ..version import __version__

APP_NAME: str = "chatinterface-server"
DEFAULT_MAIN_CONFIG: dict = {}  # will use soon
DEFAULT_APP_DIR: str = os.path.join("/", "opt", APP_NAME)


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict()

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


class ConfigMaker:
    def __init__(self, log_dir: str, conf_dir: str) -> None:
        self.log_dir: str = log_dir
        self.conf_dir: str = conf_dir

    def create_logging_config(self, log_level: str, use_console: bool = True) -> dict:
        handlers: dict = {
            'console': {
                'class': 'logging.StreamHandler',
                'stream': 'ext://sys.stdout',
                'formatter': 'default'
            }
        }
        loggers: dict = {}

        log_targets: set[str] = {
            'ws', 'auth', 'chats', 
            'database', 'main'
        }
        for target_name in log_targets:
            logfile: str = os.path.join(self.log_dir, f'{target_name}.log')
            handler_name: str = f'chatinterface.handler.{target_name}'

            logger_name: str = f'chatinterface.logger.{target_name}'
            handler_list: list[str] = [handler_name]

            if use_console:
                handler_list.append('console')

            handlers[handler_name] = {
                'class': 'logging.FileHandler',
                'formatter': 'default',
                'filename': logfile,
            }
            loggers[logger_name] = {
                'handlers': handler_list,
                'level': log_level,
                'propagate': False
            }

        return {
            'version': 1,
            'formatters': {
                'default': {
                    'format': '[%(name)s]: [%(funcName)s] - [%(asctime)s] - [%(levelname)s] - %(message)s',
                    'datefmt': '%Y-%m-%d %H:%M:%S'
                },
                'precise': {
                    'format': (
                        '[%(name)s, %(funcName)s] - [%(levelname)s] - "%(pathname)s:%(lineno)d"'
                        ' - [%(asctime)s]: %(message)s'
                    ),
                    'datefmt': '%Y-%m-%d %H:%M:%S'
                }
            },
            'handlers': handlers,
            'loggers': loggers
        }


class ConfigManager:
    def __init__(self, base_dir: str = DEFAULT_APP_DIR) -> None:
        if not base_dir:
            raise ValueError("application base directory required but is empty")
        if not os.path.isdir(base_dir):
            os.makedirs(base_dir, mode=0o755)

        # if two instances are being ran, version separates instances if base dir is same
        abs_base_dir: str = os.path.abspath(base_dir)
        ver_base_dir: str = os.path.join(abs_base_dir, __version__)

        log_dir: str = os.path.join(ver_base_dir, 'logs')
        conf_dir: str = os.path.join(ver_base_dir, 'config')

        os.makedirs(ver_base_dir, mode=0o700, exist_ok=True)
        os.makedirs(log_dir, mode=0o700, exist_ok=True)

        os.makedirs(conf_dir, mode=0o700, exist_ok=True)

        self.log_dir: str = log_dir
        self.conf_dir: str = conf_dir

        self.conf_maker: ConfigMaker = ConfigMaker(self.log_dir, self.conf_dir)
        main_config_file: str = os.path.join(self.conf_dir, 'main.json')

        main_config: dict = load_or_create_config(main_config_file, DEFAULT_MAIN_CONFIG)  # noqa

    def setup_logging(self, log_level: str = "INFO") -> None:
        log_config_file: str = os.path.join(self.conf_dir, 'log.json')
        default_logging_config: dict = self.conf_maker.create_logging_config(log_level)

        log_config: dict = load_or_create_config(log_config_file, default_logging_config)
        logging.config.dictConfig(log_config)


settings: AppSettings = AppSettings()

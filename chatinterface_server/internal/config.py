import os
import json
import logging.config

from ..version import __version__

APP_NAME: str = "chatinterface-server"
DEFAULT_MAIN_CONFIG: dict = {}  # will use soon
DEFAULT_APP_DIR: str = os.path.join("/", "opt", APP_NAME)


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

    def create_logging_config(self, log_level: str, use_console: bool = False) -> dict:
        handlers: dict = {
            'console': {
                'class': 'logging.StreamHandler',
                'stream': 'ext://sys.stdout',
                'formatter': 'default'
            }
        }
        loggers: dict = {}

        routes: set[str] = {'ws', 'auth', 'chats', 'database'}
        for route_name in routes:
            logfile: str = os.path.join(self.log_dir, f'{route_name}.log')
            handler_name: str = f'chatinterface.handler.{route_name}'

            logger_name: str = f'chatinterface.logger.{route_name}'
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

    def create_database_config(self) -> dict:
        # todo: make env override database.json or only used for first setup
        db_host: str = os.getenv('CHATINTERFACE_DB_HOST', 'localhost')
        db_port: str = os.getenv('CHATINTERFACE_DB_PORT', '3306')

        db_name: str = os.getenv("CHATINTERFACE_DB_NAME", 'chatinterface')
        db_user: str = os.getenv("CHATINTERFACE_DB_USER", 'chatinterface')

        db_password: str = os.getenv("CHATINTERFACE_DB_PASSWORD", '')
        if not db_port.isdigit():
            raise ValueError("database port is not a valid port number")
        else:
            db_port: int = int(db_port)

        db_conf: dict = {
            'mysql_config': {
                'host': db_host,
                'port': db_port,
                'db': db_name,
                'user': db_user,
                'password': db_password,
                'pool_size': 10,
                'pool_name': 'chatinterface-mysql-pool',
                'pool_reset_session': True
            },
            'executor_config': {
                'max_threads': 10,
                'thread_name_prefix': 'mysql-databaseThread-'
            }
        }
        return db_conf


class ConfigManager:
    def __init__(self, base_dir: str = DEFAULT_APP_DIR) -> None:
        if not base_dir:
            raise ValueError("application base directory required but is empty")
        if not os.path.isdir(base_dir):
            raise ValueError("application base directory does not exist, have you created it?")

        self.conf_dir: str = ''
        self.log_dir: str = ''

        self.setup_directories(base_dir)
        self.conf_maker: ConfigMaker = ConfigMaker(self.log_dir, self.conf_dir)

        main_config_file: str = os.path.join(self.conf_dir, 'main.json')
        main_config: dict = load_or_create_config(main_config_file, DEFAULT_MAIN_CONFIG)  # noqa

    def setup_directories(self, base_dir: str) -> None:
        abs_base_dir: str = os.path.abspath(base_dir)
        # if two instances are being ran, version separates instances if base dir is same
        ver_base_dir: str = os.path.join(abs_base_dir, __version__)

        log_dir: str = os.path.join(ver_base_dir, 'logs')
        conf_dir: str = os.path.join(ver_base_dir, 'config')

        os.makedirs(ver_base_dir, mode=0o700, exist_ok=True)
        os.makedirs(log_dir, mode=0o700, exist_ok=True)

        os.makedirs(conf_dir, mode=0o700, exist_ok=True)
        self.log_dir: str = log_dir

        self.conf_dir: str = conf_dir

    def setup_logging(self, log_level: str = "INFO") -> None:
        log_config_file: str = os.path.join(self.conf_dir, 'log.json')
        default_logging_config: dict = self.conf_maker.create_logging_config(log_level)

        log_config: dict = load_or_create_config(log_config_file, default_logging_config)
        logging.config.dictConfig(log_config)

    def get_database_config(self) -> dict:
        db_config_file: str = os.path.join(self.conf_dir, 'database.json')
        default_db_config: dict = self.conf_maker.create_database_config()

        db_config: dict = load_or_create_config(db_config_file, default_db_config)
        return db_config

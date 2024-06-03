# pylint: disable=all
from dotenv import load_dotenv
from os import environ

# Loads the variables of environments in the .env file
# of the current directory.
load_dotenv(environ.get("ENV_PATH", ".env"))

import logging

# Configure logging level based on the environment variable LOG_LEVEL.
# Defaults to INFO if not specified.
logging.basicConfig(
    level={
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }.get(environ.get("LOG_LEVEL", "INFO")),
    format="%(asctime)s [%(levelname)s] %(message)s",
)

from src.interfaces.chat import telegram
from src.interfaces import api
from src.database import create_tables
from threading import Thread


def start() -> None:
    create_tables()

    threads = []

    thread = Thread(target=telegram.start)
    thread.start()
    threads.append(thread)

    thread = Thread(target=api.start)
    thread.start()
    threads.append(thread)

    for t in threads:
        t.join()

import logging
import sys


def find_by_id(iterable, id):
    for item in iterable:
        if item.id == id:
            return item


FORMATTER = logging.Formatter("%(asctime)s — %(name)s — %(levelname)s — %(message)s")


def get_console_handler():
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(FORMATTER)
    return console_handler


def get_logger(logger_name, logging_level=logging.INFO):
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging_level)
    if not logger.hasHandlers():
        logger.addHandler(get_console_handler())
    logger.propagate = False
    return logger

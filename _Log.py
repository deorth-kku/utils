#!/bin/python3
import logging


def my_log_settings(log_file: str = None, log_level: str = "DEBUG") -> None:
    LOG_FORMAT = "%(asctime)s.%(msecs)03d [%(levelname)s] %(pathname)s:%(lineno)s | %(message)s "
    DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
    log_level = eval("logging.%s" % log_level.upper())
    logging.basicConfig(level=log_level,
                        format=LOG_FORMAT,
                        datefmt=DATE_FORMAT,
                        filename=log_file,
                        force=True
                        )

#!/bin/python3
import logging
from platform import python_version_tuple
from functools import wraps
import click


class MyLogSettings(object):
    def __init__(self, log_file: str = None, log_level: str = "INFO", **kwargs) -> None:
        self.log_file = log_file
        self.log_level = log_level
        self.other_args = kwargs

    def __call__(self, func):
        @ click.option("--log-file", type=click.Path(), help='using specific log file', default=self.log_file, **self.other_args)
        @ click.option("--log-level", type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], case_sensitive=False), help='using specific log level', default=self.log_level, **self.other_args)
        @wraps(func)
        def wapper_func(log_file, log_level, *args, **kwargs):
            my_log_settings(log_file, log_level)
            return func(*args, **kwargs)
        return wapper_func


def my_log_settings(log_file: str = None, log_level: str = "DEBUG") -> None:
    LOG_FORMAT = "%(asctime)s.%(msecs)03d [%(levelname)s] %(pathname)s:%(lineno)s | %(message)s "
    DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
    log_level = eval("logging.%s" % log_level.upper())
    kwargs = {
        "level": log_level,
        "format": LOG_FORMAT,
        "datefmt": DATE_FORMAT,
        "filename": log_file
    }
    if int(python_version_tuple()[1]) > 7:
        kwargs.update({"force": True})
    logging.basicConfig(**kwargs)


if __name__ == "__main__":
    pass

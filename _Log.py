#!/bin/python3
import logging
from platform import python_version_tuple


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


if __name__=="__main__":
    pass
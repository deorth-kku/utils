#!/bin/python3
import logging
from platform import python_version_tuple
from functools import wraps
import click
from utils._DoNothing import do_nothing
from typing import Tuple, Callable


def log_raise(exception: Exception):
    logging.exception(exception)
    raise exception


LOG_FORMAT = "%(asctime)s.%(msecs)03d [%(levelname)s] %(pathname)s:%(lineno)s | %(message)s "
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'


def my_log_settings(log_file: str = None, log_level: str = "DEBUG") -> None:
    log_level = eval("logging.%s" % log_level.upper()
                     ) if log_level else logging.INFO
    kwargs = {
        "level": log_level,
        "format": LOG_FORMAT,
        "datefmt": DATE_FORMAT,
        "filename": log_file
    }
    if int(python_version_tuple()[1]) > 7:
        kwargs.update({"force": True})
    logging.basicConfig(**kwargs)


class MyLogSettings(object):
    def __init__(self, log_file: str = None, log_level: str = None, **kwargs) -> None:
        self.log_file = log_file
        self.log_level = log_level
        self.set_level = None
        self.set_file = None
        self.other_args = kwargs

    def __call__(self, func: Callable) -> Callable:
        @click.option("--log-file", type=click.Path(), help='using specific log file', default=self.log_file, show_default="stderr", **self.other_args)
        @click.option("--log-level", type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], case_sensitive=False), help='using specific log level', default=self.log_level, show_default="INFO", **self.other_args)
        @wraps(func)
        def wapper_func(log_file, log_level, *args, **kwargs):
            self.set_level = log_level
            self.set_file = log_file
            if log_file == "stderr":
                log_file = None
            my_log_settings(log_file, log_level)
            return func(*args, **kwargs)
        return wapper_func

    def log_reset(self, level=None, file=None):
        '''
        resets logging args only if each of them haven't been set in command line
        '''
        kwargs = {
            "format": LOG_FORMAT,
            "datefmt": DATE_FORMAT,
            "force": True
        }
        flag = False
        if level and self.set_level == None:
            kwargs.update({"level": eval("logging.%s" % level.upper())})
            flag = True
        else:
            level0 = eval("logging.%s" % self.set_level.upper()
                          ) if self.set_level else logging.INFO
            kwargs.update({"level": level0})
        if file and self.set_file == None:
            kwargs.update({"filename": file})
            flag = True
        else:
            kwargs.update({"filename": self.set_file})
        if flag:
            logging.debug("resetting logging args: %s" % kwargs)
            logging.basicConfig(**kwargs)
        else:
            logging.debug("skipped resetting logging")


class ExceptionLogger(object):
    def __init__(self, exceptions=Exception, handler_func: Tuple[Callable, ...] = (log_raise,), finally_func: Tuple[Callable, ...] = (do_nothing,)) -> None:
        self.e_list = exceptions
        self.h_args = list(handler_func)
        self.h_func = self.h_args.pop(0)
        self.f_args = list(finally_func)
        self.f_func = self.f_args.pop(0)

    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        def wrapped_function(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except self.e_list as e:
                self.h_func(e, *self.h_args)
            finally:
                self.f_func(*self.f_args)

        return wrapped_function


if __name__ == "__main__":
    pass

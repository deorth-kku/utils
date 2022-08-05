#!/bin/python3

from functools import wraps
import logging
from utils._DoNothing import do_nothing
from typing import Tuple, Callable


def log_raise(exception: Exception):
    logging.exception(exception)
    raise exception


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

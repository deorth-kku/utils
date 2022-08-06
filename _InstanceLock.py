#!/bin/python3
import os
import sys
import platform
import hashlib
import logging
from typing import Callable
from functools import wraps


class InstanceLock(object):
    @staticmethod
    def get_temp() -> str:
        if platform.system() == "windows":
            return os.getenv("TMP")
        else:
            return "/tmp"

    def __init__(self, lock_path: str = None, when_locked_func: Callable = sys.exit, *when_locked_args, **when_locked_kwargs):
        if lock_path == None:
            self.path = os.path.join(
                self.__class__.get_temp(), hashlib.md5(__file__.encode()).hexdigest()+".lock")
        elif type(lock_path) == str:
            self.path = lock_path
        else:
            raise ValueError("ircorrect lock path %s" % lock_path)

        self.wlf = when_locked_func
        self.wla = when_locked_args
        self.wlk = when_locked_kwargs

        self.acquired = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release_lock()

    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        def wrapped_function(*args, **kwargs):
            try:
                self.check_exit()
                return func(*args, **kwargs)
            finally:
                self.release_lock()
        return wrapped_function

    def get_lock(self) -> int:
        if os.path.isfile(self.path):
            logging.warning("lock file %s already existed!" % self.path)
            with open(self.path, "r") as f:
                instance = int(f.read())
            return instance
        else:
            logging.debug("lock file %s not existed, creating" % self.path)
            with open(self.path, "w") as f:
                f.write(str(os.getpid()))
                self.acquired = True
            return False

    def check_exit(self) -> None:
        apid = self.get_lock()
        if apid:
            logging.error(
                "Another Instance is running at %s, not starting" % apid)
            self.wlf(*self.wla, **self.wlk)

    def release_lock(self) -> None:
        if self.acquired:
            logging.debug("remove lock %s" % self.path)
            os.remove(self.path)


if __name__ == "__main__":
    pass

#!/bin/python3
import logging
def do_nothing(*_):
    pass

class DoNothing():
    def __init__(self) -> None:
        pass

    def __getattr__(self, name):
        logging.debug("method %s is called, but it does nothing"%name)
        return do_nothing



if __name__=="__main__":
    pass
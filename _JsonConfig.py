
#!/bin/python3
import json
from collections import UserDict
from copy import deepcopy
import logging
from typing import Iterable


class JsonConfig(UserDict):
    @staticmethod
    def mergeDict(a: dict, b: dict):
        newdict = deepcopy(a)
        for key in b:
            typeflag = type(b[key])
            if typeflag == dict:
                if key in a:
                    newvalue = JsonConfig.mergeDict(a[key], b[key])
                else:
                    newvalue = b[key]
            elif typeflag == set:
                newvalue = deepcopy(a[key])
                for bb in b[key]:
                    newvalue.add(bb)
            elif typeflag == list or typeflag == tuple:
                newvalue = a[key]+b[key]
            else:
                newvalue = b[key]
            newdict.update({key: newvalue})
        return newdict

    @staticmethod
    def replace(config: dict, var_key: str, var_value: str) -> dict:
        typeflag = type(config)
        if typeflag == str:
            if var_key == config:
                return var_value
            elif type(var_value) == str and var_key in config:
                return config.replace(var_key, var_value)
            else:
                return config
        elif typeflag == int or typeflag == float or typeflag == bool or config == None:
            return config
        elif typeflag == dict:
            for key in config:
                newvalue = JsonConfig.replace(config[key], var_key, var_value)
                config.update({key: newvalue})
            return config
        else:
            new = []
            for key in config:
                new_key = JsonConfig.replace(key, var_key, var_value)
                new.append(new_key)
            return typeflag(new)

    def __init__(self, file: str, mode: str = "rw") -> None:
        self.file = file
        self.mode = mode
        if mode == "w":  # write only
            self.data = {}
        elif mode == "r":  # read only, throw error when not exist
            self.read_file()
        elif mode == "rw":
            try:
                self.read_file()
            except FileNotFoundError:
                logging.warning("creating not existed file %s" % self.file)
                self.data = {}
        else:
            raise ValueError("Unknown mode %s" % mode)

    def read_file(self):
        with open(self.file, 'r', encoding='utf-8') as f:
            self.data = json.load(f)

    def var_replace(self, key: str, value: str):
        self.data = self.replace(self.data, key, value)

    def set_defaults(self, defaults: dict):
        self.data = self.mergeDict(defaults, self.data)

    def dumpconfig(self, config: dict = None, sort_keys: bool = False, indent: int = 4, separators: Iterable[str] = (',', ': '), ensure_ascii: bool = False, **kwargs):
        if self.mode == "r":
            raise ValueError(
                "Not allow to write when opened on read-only mode")
        if config == None:
            config = self.data
        with open(self.file, "w", encoding='utf-8') as f:
            json.dump(config, f, sort_keys=sort_keys, indent=indent,
                      separators=separators, ensure_ascii=ensure_ascii, **kwargs)


if __name__ == "__main__":
    pass

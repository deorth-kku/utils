
#!/bin/python3
import json
from collections import UserDict
from copy import deepcopy
import logging


class JsonConfig(UserDict):
    @staticmethod
    def mergeDict(a, b):
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
    def replace(config, var_key, var_value):
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

    def __init__(self, file: str, mode="rw"):
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

    def var_replace(self, key, value):
        self.data = self.replace(self.data, key, value)

    def set_defaults(self, defaults):
        self.data = JsonConfig.mergeDict(defaults, self.data)

    def dumpconfig(self, config=None):
        if self.mode == "r":
            raise ValueError(
                "Not allow to write when opened on read-only mode")
        if config == None:
            config = self.data
        with open(self.file, "w", encoding='utf-8') as f:
            json.dump(config, f, sort_keys=True,
                      indent=4, separators=(',', ': '), ensure_ascii=False)


if __name__ == "__main__":
    from _Log import my_log_settings
    my_log_settings()
    # test rw on not exist file
    JsonConfig("foobar.json", "rw").dumpconfig({"aaa": "bbb"})
    # test r on not exist file
    import os
    import logging
    os.remove("foobar.json")
    try:
        JsonConfig("foobar.json", "r").dumpconfig({"aaa": "bbb"})
    except Exception as e:
        logging.exception(e)

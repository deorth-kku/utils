
#!/bin/python3
import json
from collections import UserDict
from copy import deepcopy

class JsonConfig(UserDict):
    @staticmethod
    def mergeDict(a, b):
        newdict = deepcopy(a)
        for key in b:
            typeflag = type(b[key])
            if typeflag == dict:
                newvalue = JsonConfig.mergeDict(a[key], b[key])
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
    def replace(config,var_key,var_value):
        typeflag = type(config)
        if typeflag==str:
            if var_key == config:
                return var_value
            elif type(var_value)==str and var_key in config:
                return config.replace(var_key,var_value)
            else:
                return config
        elif typeflag==int or typeflag==float or typeflag==bool or config==None:
            return config
        elif typeflag==dict:
            for key in config:
                newvalue = JsonConfig.replace(config[key],var_key, var_value)
                config.update({key:newvalue})
            return config
        else:
            new=[]
            for key in config:
                new_key = JsonConfig.replace(key,var_key,var_value)
                new.append(new_key)
            return typeflag(new)

    
    def __init__(self, file):
        self.file = file
        try:
            with open(file, 'r',encoding='utf-8') as f:
                self.data = json.load(f)
        except (IOError, json.decoder.JSONDecodeError):
            self.data = {}


    def var_replace(self,key,value):
        self.data=self.replace(self.data,key,value)

    def set_defaults(self,defaults):
        self.data=JsonConfig.mergeDict(defaults,self.data)


    def dumpconfig(self, config=None):
        if config==None:
            config=self.data
        with open(self.file, "w",encoding='utf-8') as f:
            json.dump(config, f, sort_keys=True,
                      indent=4, separators=(',', ': '),ensure_ascii=False)

if __name__ == "__main__":
    pass
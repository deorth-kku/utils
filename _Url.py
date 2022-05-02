#!/bin/python3
import os
class Url:
    @staticmethod
    def join(*args):
        """
        Joins given arguments into an url. Trailing but not leading slashes are
        stripped for each argument.
        """
        return "/".join(map(lambda x: str(x).rstrip('/'), args))
    @staticmethod
    def basename(url):
        filename=os.path.basename(url)
        return filename.split("?")[0]
    @staticmethod
    def sitename(url):
        parts=url.split("/")
        return parts[0]+"//"+parts[2]
if __name__ == "__main__":
    pass
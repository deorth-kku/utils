#!/bin/python3
import logging
import xmlrpc.client
import time
import subprocess
from copy import copy
from pprint import pprint
import logging
try:
    import requests
except ImportError:
    logging.warning("requests not installed, you cannot use jsonrpc api!")


class DownloadError(Exception):
    def __init__(self, status):
        Exception.__init__(self)
        self.message = "Download failed, Download task is %s" % status

    def __str__(self):
        return repr(self.message)


class Aria2Rpc():
    @staticmethod
    def progressBar(current, total, speed):
        if total == 0:
            total = 1
        if current > total:
            current = total
        current = current
        total = total
        if speed < 1048756:
            speed = str(int(speed/1024))+"KB/S "
        else:
            speed = str(round(speed/1048756, 2))+"MB/S"
        per = round(current/total*100, 1)
        percent = str(per)+"%"
        n = int(per/5)
        i = int(per % 5)
        list = ['  ', '▍ ', '▊ ', '█ ', '█▍']
        if per == 100:
            bar = " |"+"██"*n+"| "
        else:
            bar = " |"+"██"*n+list[i]+"  "*(19-n)+"| "
        print(bar+percent+"  "+str(round(current/1048756, 1))+"MB/" +
              str(round(total/1048756, 1))+"MB "+speed+"      ", end="\r")

    @staticmethod
    def readAria2Conf(conf_path):
        conf = {}
        f = open(conf_path, "r")
        for line in f.readlines():
            line = line.split(r"#")[0]
            kv = line.split(r"=")
            if len(kv) == 2:
                conf.update({line[0]: line[1]})
            else:
                continue
        f.close()

    bin_path = "aria2c"

    @classmethod
    def setAria2Bin(cls, bin_path):
        cls.bin_path = bin_path

    def __init__(self, ip: str = "127.0.0.1", port: int = 6800, passwd: str = "", api: str = "xmlrpc", args={}):  # rework to use **kwargs
        self.tasks = []
        self.api = api
        self.secret = "token:"+passwd
        if api == "xmlrpc":
            connection = xmlrpc.client.ServerProxy(
                "http://%s:%s/rpc" % (ip, port))
            self.aria2 = connection.aria2
        elif api == "jsonrpc":
            self.connection_url = "http://%s:%s/jsonrpc" % (ip, port)
        else:
            raise ValueError("Unsupported api type %s" % api)
        try:
            self.getVersion()
        except ConnectionRefusedError:
            if ip == "127.0.0.1" or ip == "localhost" or ip == "127.1":
                cmd = [
                    self.bin_path,
                    "--no-conf",
                    "--enable-rpc=true",
                    "--rpc-allow-origin-all=true",
                    "--rpc-listen-port=%s" % port
                ]
                for arg in args:
                    if len(arg) != 1:
                        arg_str = "--%s=%s" % (arg, args[arg])
                    else:
                        arg_str = "-%s=%s" % (arg, args[arg])
                    cmd.append(arg_str)
                if passwd != "":
                    cmd.append("--rpc-secret=%s" % passwd)
                self.process = subprocess.Popen(
                    cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                raise
        except (xmlrpc.client.Fault,AttributeError):
            logging.error("aria2 rpc password ircorrect")
            raise ValueError("password ircorrect")

    def __getattr__(self, name):
        def __defaultMethod(*args):
            newargs = (self.secret,) + args
            if self.api == "xmlrpc":
                method = getattr(self.aria2, name)
                try:
                    return method(*newargs)
                except xmlrpc.client.Fault as e:
                    raise AttributeError(e)
            elif self.api == "jsonrpc":
                jsonreq = {
                        'jsonrpc': '2.0', 
                        'id': 'Aria2Rpc',
                        'method': 'aria2.'+name,
                        'params': newargs
                        }
                try:
                    rsp=requests.post(url=self.connection_url,json=jsonreq)
                except requests.exceptions.ConnectionError as e:
                    raise ConnectionRefusedError(e)
                jsonrsp=rsp.json()
                if "result" in jsonrsp:
                    return jsonrsp["result"]
                raise AttributeError(jsonrsp["error"])
                

        return __defaultMethod

    def download(self, url: str, pwd: str, filename: str = None, proxy: str = "", **raw_opts):
        opts = {
            "dir": pwd,
            "all-proxy": proxy
        }
        for key in raw_opts:
            new_key = key.replace("_", "-")
            value = raw_opts[key]
            opts.update({new_key: value})
        if filename != None:
            opts.update({"out": filename})

        req = self.addUri([url], opts)
        task = Aria2Task(req, self)
        self.tasks.append(task)
        return task

    def wget(self, url: str, pwd: str, filename: str = None, retry: int = 5, proxy: str = "", del_failed_task: bool = True, **raw_opts):
        full_retry = copy(retry)
        task = False
        while True:
            if del_failed_task and task:
                task.removeDownloadResult()
            task = self.download(url, pwd, filename, proxy=proxy, **raw_opts)
            status = task.tellStatus()['status']
            while status == 'active' or status == 'paused':
                time.sleep(0.1)
                r = task.tellStatus()
                status = r['status']
                self.__class__.progressBar(int(r['completedLength']), int(
                    r['totalLength']), int(r['downloadSpeed']))
            if status != 'complete':
                if retry <= 0:
                    raise DownloadError(r["errorMessage"])
                else:
                    retry -= 1
                    print("%s, gonna retry %s/%s" %
                          (r["errorMessage"], full_retry-retry, full_retry))
                    time.sleep(1)
                    continue
            else:
                break

    def quit(self):
        try:
            self.process.terminate()
            self.process.wait()
        except AttributeError:
            pass


class Aria2Task():
    def __init__(self, gid: str, rpc_obj: Aria2Rpc) -> None:
        self.rpc = rpc_obj
        self.gid = gid

    def __getattr__(self, name):
        def __defaultMethod(*args):
            newargs = (self.gid,) + args
            method = getattr(self.rpc, name)
            return method(*newargs)
        return __defaultMethod

    def retry(self, del_failed_task: bool = True):
        pass


if __name__ == "__main__":
    a=Aria2Rpc(passwd="pandownload",api="jsonrpc")
    a.wget("http://baidu.com",pwd="/mnt/temp")

#!/bin/python3
import logging
import xmlrpc.client
import time
import subprocess
from copy import copy
import logging
try:
    import requests
    from http.client import HTTPException
except ImportError:
    logging.warning("requests not installed, you cannot use jsonrpc api!")


class DownloadError(Exception):
    def __init__(self, msg: str) -> None:
        Exception.__init__(self)
        self.message = "Download failed, error message: %s" % msg

    def __str__(self) -> str:
        return repr(self.message)


class Aria2Task():
    def __init__(self, gid: str, rpc_obj) -> None:
        self.rpc = rpc_obj  # Aria2Rpc object
        self.gid = gid

    def __getattr__(self, name):
        def __defaultMethod(*args):
            newargs = (self.gid,) + args
            method = getattr(self.rpc, name)
            return method(*newargs)
        return __defaultMethod

    def __str__(self) -> str:
        return self.gid

    def __bool__(self) -> bool:
        return self.is_running()

    def retry(self, remove_failed_task: bool = True) -> bool:
        r = self.tellStatus()
        status = r["status"]
        if status == "error":
            if len(r["files"]) != 1:
                raise ValueError("No support for bittorrent/magnet for now")
            urls = [url["uri"] for url in r["files"][0]["uris"]]
            urls = list(set(urls))
            options = self.getOption()
            if remove_failed_task:
                rsp = self.removeDownloadResult()
                logging.debug("removed failed task gid %s %s" %
                              (self.gid, rsp))
            rsp = self.rpc.addUri(urls, options)
            logging.info("retry failed task %s as new task %s" %
                         (self.gid, rsp))
            self.gid = rsp

    def is_running(self) -> bool:
        status = self.get_status()
        logging.debug("task gid %s status is %s" % (self.gid, status))
        if status in ("running", "waiting", "paused"):
            return True
        else:
            return False

    def get_status(self) -> str:
        status = self.tellStatus()['status']
        return status


class Aria2Rpc():
    @staticmethod
    def progressBar(current: int, total: int, speed: int, end="\r"):
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
              str(round(total/1048756, 1))+"MB "+speed+"      ", end=end)

    @staticmethod
    def readAria2Conf(conf_path: str) -> dict:
        conf = {}
        f = open(conf_path, "r")
        for line in f.readlines():
            line = line.split(r"#")[0]
            kv = line.split(r"=")
            if len(kv) == 2:
                conf.update({kv[0]: kv[1]})
            else:
                continue
        f.close()
        return conf

    bin_path = "aria2c"

    @classmethod
    def setAria2Bin(cls, bin_path: str) -> None:
        cls.bin_path = bin_path

    def __init__(self, host: str = "127.0.0.1", port: int = 6800, passwd: str = "", protocal: str = "http", api: str = "xmlrpc", **kwargs) -> None:  # rework to use **kwargs
        self.tasks = []
        self.api = api
        self.secret = "token:"+passwd
        if api == "xmlrpc":
            connection = xmlrpc.client.ServerProxy(
                "%s://%s:%s/rpc" % (protocal, host, port))
            self.aria2 = connection.aria2
        elif api == "jsonrpc":
            self.connection_url = "%s://%s:%s/jsonrpc" % (protocal, host, port)
        else:
            raise ValueError("Unsupported api type %s" % api)
        try:
            self.getVersion()
        except ConnectionRefusedError:
            if host in ("127.0.0.1", "localhost", "127.1"):
                logging.warning(
                    "Failed to connect aria2 rpc at port %s, starting aria2 subprocess now" % port)
                self.config = kwargs
                self.config.update({
                    "rpc_listen_port": port,
                    "rpc_secret": passwd,
                    "enable_rpc": "true"
                })
                self.start()
            else:
                raise
        except (xmlrpc.client.Fault, AttributeError):
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
                    rsp = requests.post(url=self.connection_url, json=jsonreq)
                except requests.exceptions.ConnectionError as e:
                    raise ConnectionRefusedError(e)
                if not rsp.ok:
                    logging.critical("rpc server return a error status code %s, message: %s" % (
                        rsp.status_code, rsp.text))
                    raise HTTPException(rsp.status_code, rsp.text)
                jsonrsp = rsp.json()
                if "result" in jsonrsp:
                    return jsonrsp["result"]
                raise AttributeError(jsonrsp["error"])

        return __defaultMethod

    def __exit__(self, exc_type, exc_value, traceback):
        self.quit()

    def start(self) -> None:
        cmd = [self.bin_path, "--no-conf"]
        for arg in self.config:
            if len(arg) > 1:
                arg_str = "--%s=%s" % (arg.replace("_", "-"), self.config[arg])
            else:
                arg_str = "-%s=%s" % (arg.replace("_", "-"), self.config[arg])
            cmd.append(arg_str)
        self.process = subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.process.cmd = " ".join(cmd)
        logging.debug("started subrprocess cmd %s, pid %s" %
                      (self.process.cmd, self.process.pid))
        for i in range(10):
            try:
                self.getVersion()
                return
            except ConnectionError:
                time.sleep(0.1)
        logging.critical(
            "cannot connect to aria rpc after 1s, please check your args %s" % self.config)

    def download(self, url: str, pwd: str, filename: str = None, proxy: str = "", **raw_opts) -> Aria2Task:
        opts = {
            "dir": pwd,
            "all-proxy": proxy
        }
        for key in raw_opts:
            new_key = key.replace("_", "-")
            value = raw_opts[key]
            if type(value) == bool:
                value = str(value).lower()
            opts.update({new_key: value})
        if filename != None:
            opts.update({"out": filename})

        req = self.addUri([url], opts)
        task = Aria2Task(req, self)
        self.tasks.append(task)
        return task

    def wget(self, url: str, pwd: str, filename: str = None, retry: int = 5, proxy: str = "", remove_failed_task: bool = True, refresh_interval: float = 0.1, **raw_opts) -> Aria2Task:
        retry_left = copy(retry)
        task = self.download(url, pwd, filename, proxy=proxy, **raw_opts)
        while True:
            r = task.tellStatus()
            status = r['status']
            if status == "error":
                if retry_left <= 0:
                    logging.error("download task %s error after %s retry, error message: %s" % (
                        task.gid, retry, r["errorMessage"]))
                    raise DownloadError(r["errorMessage"])
                else:
                    logging.warning("%s, gonna retry %s/%s" %
                                    (r["errorMessage"], retry-retry_left+1, retry))
                    task.retry(remove_failed_task)
                    retry_left -= 1
            elif status in ("active", "paused", "waiting"):
                self.__class__.progressBar(int(r['completedLength']), int(
                    r['totalLength']), int(r['downloadSpeed']))
                time.sleep(refresh_interval)
            elif status == "complete":
                logging.debug("task %s complete" % task.gid)
                self.__class__.progressBar(int(r['completedLength']), int(
                    r['totalLength']), int(r['downloadSpeed']), end="\n")
                return task
            elif status == "removed":
                error_str = "task %s removed by user, exiting" % task.gid
                logging.warning(error_str)
                raise RuntimeError(error_str)
            else:
                error_str = "undefined status %s" % status
                logging.critical(error_str)
                raise ValueError(error_str)

    def quit(self):
        if "process" in self.__dict__:
            logging.debug("calling shutdown for aria2 at port %s" %
                          self.config["rpc_listen_port"])
            self.shutdown()
            self.process.wait()
            logging.info("subprocess shutdown success, cmd %s, pid %s" %
                         (self.process.cmd, self.process.pid))

    def __exit__(self):
        logging.debug("__exit__ method for Aria2Rpc has been called")
        return True

    def __del__(self):
        logging.debug("__del__ method for Aria2Rpc has been called")
        return True


if __name__ == "__main__":
    from _Log import my_log_settings
    my_log_settings()
    a = Aria2Rpc(host="127.0.0.1", protocal="http",
                 passwd="abc", port=6801, api="xmlrpc")
    try:
        a.wget("http://baidfdu.com/123123123123",
               pwd="/mnt/temp", allow_overwrite="false", retry=1)
    except Exception as e:
        logging.critical(e)
        raise
    finally:
        a.quit()

#!/bin/python3
import os
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

if __package__ == None:
    from _DoNothing import do_nothing
else:
    from ._DoNothing import do_nothing


class DownloadError(Exception):
    def __init__(self, msg: str) -> None:
        Exception.__init__(self)
        self.message = "Download failed, error message: %s" % msg

    def __str__(self) -> str:
        return repr(self.message)


class Aria2Task():
    def __init__(self, gid: str, rpc_obj: object) -> None:
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

    def __eq__(self, __o: object) -> bool:
        return self.gid == __o.gid and self.rpc == __o.rpc

    def __hash__(self) -> int:
        return hash(self.gid)

    def retry(self, remove_failed_task: bool = True) -> object:
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
            options.update({
                "gid": self.gid
            })
            rsp = self.rpc.addUri(urls, options)
            logging.info("retry failed task %s" % self.gid)
            return self
        else:
            return self

    def is_running(self) -> bool:
        status = self.get_status()
        logging.debug("task gid %s status is %s" % (self.gid, status))
        if status in ("active", "waiting", "paused"):
            return True
        else:
            return False

    def get_status(self) -> str:
        status = self.tellStatus()['status']
        return status

    def wait(self, interval: int = 1) -> None:
        while self.is_running():
            time.sleep(interval)


class Aria2Rpc():
    @staticmethod
    def unitconv(unit_Bytes: int) -> str:
        if unit_Bytes < 1024:
            num = float(unit_Bytes)
            unit = 'B'
        elif unit_Bytes < 1048756:
            num = unit_Bytes/1024
            unit = 'KB'
        elif unit_Bytes < 1073741824:
            num = unit_Bytes/1048756
            unit = 'MB'
        else:
            num = unit_Bytes/1073741824
            unit = 'GB'
        if num >= 100 or unit == 'B':
            out = "%.0f%s" % (num, unit)
        else:
            out = '{0:.3}{1}'.format(num, unit)
        return out

    @staticmethod
    def progressBar(current: int, total: int, speed: int) -> None:
        if current > total:
            current = total

        speed_str = Aria2Rpc.unitconv(speed)+"/S"
        current_str = Aria2Rpc.unitconv(current)
        total_str = Aria2Rpc.unitconv(total)
        if total == 0:
            percent = float(0)
        else:
            percent = current/total*100
        percent_str = "{0: >3.0f}%".format(percent)

        width = os.get_terminal_size().columns

        bar_width = width-32
        if bar_width <= 0:
            bar = ""
        else:
            bar_used = int(bar_width*(percent/100))
            bar_space = bar_width-bar_used
            bar = "[%s%s]" % ("█"*bar_used, " "*bar_space)

        space_num = width-len(bar+percent_str +
                              current_str+total_str+speed_str)-6
        out_str = "\r%s %s %s %s/%s %s" % (bar, percent_str,
                                           " "*space_num, current_str, total_str, speed_str)
        print(out_str, end="")

    @staticmethod
    def readAria2Conf(conf_path: str) -> dict:
        conf = {}
        f = open(conf_path, "r")
        for line in f.readlines():
            line = line.rstrip("\n")
            line = line.split(r"#")[0]
            kv = line.split(r"=")

            if len(kv) == 2:
                key, value = kv
                value = value.strip()
                conf.update({key: value})
            else:
                continue
        f.close()
        return conf

    @staticmethod
    def kwargs_process(kwargs: dict) -> dict:
        new_args = {}
        for key in kwargs:
            new_key = key.replace("_", "-")
            value = kwargs[key]
            if type(value) == bool:
                value = str(value).lower()
            elif value == None:
                continue
            new_args.update({new_key: value})
        return new_args

    bin_path = "aria2c"

    @classmethod
    def setAria2Bin(cls, bin_path: str) -> None:
        cls.bin_path = bin_path

    def __init__(self, host: str = "127.0.0.1", port: int = 6800, passwd: str = None, protocal: str = "http", api: str = "xmlrpc", **kwargs) -> None:  # rework to use **kwargs
        self.tasks = set()
        self.api = api
        self.secret = "token:%s" % passwd
        self.config = kwargs
        if api == "xmlrpc":
            connection = xmlrpc.client.ServerProxy(
                "%s://%s:%s/rpc" % (protocal, host, port))
            self.aria2 = connection.aria2
        elif api == "jsonrpc":
            self.connection_url = "%s://%s:%s/jsonrpc" % (protocal, host, port)
        else:
            raise ValueError("Unsupported api type %s" % api)
        try:
            self.sessionID = self.getSessionInfo()['sessionId']
        except ConnectionRefusedError:
            if host in ("127.0.0.1", "localhost", "127.1"):
                logging.warning(
                    "Failed to connect aria2 rpc at port %s, starting aria2 subprocess now" % port)
                self.config.update({
                    "rpc_listen_port": port,
                    "rpc_secret": passwd,
                    "enable_rpc": True
                })
                self.start()
            else:
                raise
        except (xmlrpc.client.Fault, RuntimeError):
            logging.error("aria2 rpc password ircorrect")
            raise ValueError("password ircorrect")

    def __getattr__(self, name):

        def __defaultMethod(*args):
            if self.secret == "token:None":
                newargs = args
            else:
                newargs = (self.secret,) + args
            logging.debug("calling rpc method: %s, args: %s" %
                          (name, str(newargs)))
            if self.api == "xmlrpc":
                method = getattr(self.aria2, name)
                try:
                    result = method(*newargs)
                except xmlrpc.client.Fault as e:
                    raise RuntimeError(e)

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
                    result = jsonrsp["result"]
                else:
                    raise RuntimeError(jsonrsp["error"])
            if logging.root.isEnabledFor(logging.DEBUG):
                logging.debug("rpc method: %s, result: %s" %
                              (name, str(result)))
            return result

        return __defaultMethod

    def __str__(self) -> str:
        return self.sessionID

    def __hash__(self) -> int:
        hash(self.sessionID)

    def __eq__(self, __o: object) -> bool:
        return self.sessionID == __o.sessionID

    def start(self) -> None:
        cmd = [self.bin_path, "--no-conf"]
        args = self.kwargs_process(self.config)
        for arg in args:
            if len(arg) > 1:
                arg_str = "--%s=%s" % (arg, args[arg])
            else:
                arg_str = "-%s=%s" % (arg, args[arg])
            cmd.append(arg_str)
        self.process = subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.process.cmd = " ".join(cmd)
        logging.debug("started subrprocess cmd %s, pid %s" %
                      (self.process.cmd, self.process.pid))
        for i in range(10):
            try:
                self.sessionID = self.getSessionInfo()['sessionId']
                return
            except ConnectionError:
                time.sleep(0.1)
        logging.critical(
            "cannot connect to aria rpc after 1s, please check your args %s" % self.config)

    def download(self, url: list, pwd: str = None, filename: str = None, proxy: str = None, **raw_opts) -> Aria2Task:
        # use session config
        if "process" in self.__dict__:
            task_opts = {}
        else:
            task_opts = self.kwargs_process(self.config)

        # convert url or urls addUri
        if type(url) == str:
            url = [url]

        # old args compatiblity
        method_opts = {
            "dir": pwd,
            "all-proxy": proxy,
            "out": filename
        }
        for opt in method_opts:
            if method_opts[opt] != None:
                task_opts.update({opt: method_opts[opt]})

        # process raw args for addUri format
        task_opts.update(self.kwargs_process(raw_opts))

        req = self.addUri(url, task_opts)
        logging.info("Started download %s as task %s" % (url, req))
        task = Aria2Task(req, self)
        self.tasks.add(task)
        return task

    def wget(self, url: str, pwd: str = None, filename: str = None, retry: int = 5, proxy: str = None, remove_failed_task: bool = True, progress_bar: bool = True, refresh_interval: float = 0.1, **raw_opts) -> Aria2Task:
        retry_left = copy(retry)
        task = self.download(url, pwd, filename, proxy=proxy, **raw_opts)
        try:
            os.get_terminal_size()
        except (OSError, ValueError):
            progress_bar = False
        if progress_bar:
            logging.debug("using progress bar")
            pbar = self.progressBar
        else:
            logging.debug("disable progress bar")
            pbar = do_nothing
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
                pbar(int(r['completedLength']), int(
                    r['totalLength']), int(r['downloadSpeed']))
                time.sleep(refresh_interval)
            elif status == "complete":
                pbar(int(r['completedLength']), int(
                    r['totalLength']), int(r['downloadSpeed']))
                logging.info("task %s complete" % task.gid)
                return task
            elif status == "removed":
                error_msg = "task %s removed by user, exiting" % task.gid
                logging.warning(error_msg)
                raise RuntimeError(error_msg)
            else:
                error_msg = "undefined status %s" % status
                logging.critical(error_msg)
                raise ValueError(error_msg)

    def quit(self):
        if "process" in self.__dict__:
            logging.debug("calling shutdown for aria2 at port %s, sessionID: %s" %
                          (self.config["rpc_listen_port"], self.sessionID))
            self.shutdown()
            self.process.wait()
            logging.info("subprocess shutdown success, cmd %s, pid %s" %
                         (self.process.cmd, self.process.pid))
            delattr(self, "process")

    def __del__(self):
        logging.debug("__del__ method for Aria2Rpc has been called")
        self.quit()
        return True


if __name__ == "__main__":
    # Test for Aria2Rpc, if this throw some uncaught error, it means something is wrong.
    # Set logs first
    from _Log import my_log_settings
    my_log_settings()

    temp_dir = "/mnt/temp"
    dl_url = "https://www.baidu.com/index.html"
    # Start one on 6801
    a = Aria2Rpc(host="127.0.0.1", protocal="http", passwd="abc", port=6801, allow_overwrite=True,
                 rpc_listen_all=True, rpc_allow_origin_all=True, auto_file_renaming=False)
    try:
        # Remove download file if exists
        download_file = os.path.join(temp_dir, os.path.basename(dl_url))
        if os.path.exists(download_file):
            os.remove(download_file)
        # A normal test download, this should not be a problem, unless dl_url is invaild.
        a.wget(dl_url, dir=temp_dir)
        # Now check again
        logging.debug("check if download file %s exists: %s" %
                      (download_file, os.path.exists(download_file)))
        # now download again, since we set allow_overwrite=True on start, this shouldn't be a problem either.
        a.wget(dl_url, dir=temp_dir)

        # Now we connect to last create aria2 process, but added option allow_overwrite=False, to test if it raise error. To test more potential problem, we use jsonrpc this time.
        b = Aria2Rpc(passwd="abc", port=6801,
                     api="jsonrpc", allow_overwrite=False)
        # Try download the same file
        try:
            b.wget(dl_url, dir=temp_dir, retry=1)
        except DownloadError as e:
            # Check log if aria2 tell us there is a duplicate file
            logging.debug(e)

        # Tell aria2 to exit gracefully, remove temp file also
        os.remove(download_file)
    except (KeyboardInterrupt, Exception):
        raise
    finally:
        a.quit()

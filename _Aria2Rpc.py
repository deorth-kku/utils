#!/bin/python3
import logging
import xmlrpc.client
import time
import subprocess
from copy import copy

class DownloadError(Exception):
    def __init__(self, status):
        Exception.__init__(self)
        self.message = "Download failed, Download task is %s" % status

    def __str__(self):
        return repr(self.message)

class Aria2Rpc:
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
        conf={}
        f=open(conf_path,"r")
        for line in f.readlines():
            line=line.split(r"#")[0]
            kv=line.split(r"=")
            if len(kv)==2:
                conf.update({line[0]:line[1]})
            else:
                continue
        f.close()


    bin_path="aria2c"
    @classmethod
    def setAria2Bin(cls,bin_path):
        cls.bin_path=bin_path

    def __init__(self, ip, port="6800", passwd="",args={}):
        connection = xmlrpc.client.ServerProxy(
            "http://%s:%s/rpc" % (ip, port))
        self.aria2 = connection.aria2
        self.secret = "token:"+passwd
        self.tasks = []
        self.methodname = None
        try:
            self.aria2.getVersion(self.secret)
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
                    if len(arg)!=1:
                        arg_str="--%s=%s"%(arg,args[arg])
                    else:
                        arg_str="-%s=%s"%(arg,args[arg])
                    cmd.append(arg_str)

                if passwd != "":
                    cmd.append("--rpc-secret=%s" % passwd)
                self.process = subprocess.Popen(cmd,stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                raise
        except xmlrpc.client.Fault:
            logging.error("aria2 rpc password ircorrect")
            raise ValueError("password ircorrect")
    
    def __getattr__(self, name):
        self.methodname = name
        return self.__defaultMethod


    def __defaultMethod(self,*args):
        if self.methodname != None:
            newargs = (self.secret,) + args
            method = getattr(self.aria2, self.methodname)
            self.methodname = None
            return method(*newargs)

    
    def download(self, url, pwd, filename=None,proxy="",**raw_opts):
        opts={
            "dir":pwd,
            "all-proxy":proxy
        }
        for key in raw_opts:
            new_key=key.replace("_","-")
            value=raw_opts[key]
            opts.update({new_key:value})
        if filename!=None:
            opts.update({"out":filename})

        req = self.addUri([url], opts)
        self.tasks.append(req)
        return req

    def wget(self, url, pwd, filename=None,retry=5,proxy="",del_failed_task=True,**raw_opts):
        full_retry=copy(retry)
        req=False
        while True:
            if del_failed_task and  req:
                self.removeDownloadResult(req)
            req = self.download(url, pwd, filename,proxy=proxy,**raw_opts)
            status = self.tellStatus(req)['status']
            while status == 'active' or status == 'paused':
                time.sleep(0.1)
                r = self.tellStatus(req)
                status = r['status']
                Aria2Rpc.progressBar(int(r['completedLength']), int(
                    r['totalLength']), int(r['downloadSpeed']))
            if status != 'complete':
                if retry<=0:
                    raise DownloadError(r["errorMessage"])
                else:
                    retry-=1
                    print("%s, gonna retry %s/%s"%(r["errorMessage"],full_retry-retry,full_retry))
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


if __name__ == "__main__":
    pass
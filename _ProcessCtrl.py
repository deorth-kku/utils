#!/bin/python3
import logging
import os
import sys
import platform
import subprocess
import psutil
import ctypes


class ProcessCtrl:
    platform_info = platform.platform().split("-")
    OS = platform_info[0].lower()

    if OS == "windows":
        service_type = "windows"
    elif OS == "linux":
        if os.path.exists("/usr/bin/systemd"):
            service_type = "systemd"
        else:
            service_type = "init"
    else:
        print("not supported OS type %s" % OS)

    @staticmethod
    def Service(service_name, command):
        if ProcessCtrl.service_type == "windows":
            cmd = ["net", command, service_name]
        elif ProcessCtrl.service_type == "init":
            cmd = ["service", service_name, command]
        elif ProcessCtrl.service_type == "systemd":
            cmd = ["systemctl", command, service_name]

        subprocess.call(cmd, stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL)

    @staticmethod
    def popup_msg(title,msg=None):
        if msg == None:
            msg = title
        if ProcessCtrl.OS == "windows":
            return ctypes.windll.user32.MessageBoxW(0, msg, msg, 0)
        else:
            logging.debug("popup msg is not supported on %s (yet)" %
                          ProcessCtrl.OS)

    def __init__(self, process_name, service=False):
        self.process_name = process_name
        self.service = service
        if service:
            pass
        else:
            self.flushProc()

    def flushProc(self):
        self.procs = []
        for proc in psutil.process_iter():
            if proc.name() == self.process_name:
                self.procs.append(proc)

    def checkProc(self):
        self.flushProc()
        if len(self.procs) != 0:
            return True
        else:
            return False

    def waitProc(self):
        self.flushProc()
        for proc in self.procs:
            psutil_proc = psutil.Process(pid=proc.pid)
            psutil_proc.wait()

    def stopProc(self):
        if self.service:
            self.Service(self.process_name, "stop")
        else:
            self.flushProc()
            self.cmds = []
            for proc in self.procs:
                self.cmds.append((proc.cmdline(), proc.cwd()))
                proc.kill()

    def startProc(self):
        if self.service:
            self.Service(self.process_name, "start")
        else:
            for cmd in self.cmds:
                sys.path.append(cmd[1])
                subprocess.Popen(cmd[0], cwd=cmd[1])
                sys.path.pop()

    def restartProc(self):
        self.stopProc()
        self.startProc()


if __name__ == "__main__":
    pass

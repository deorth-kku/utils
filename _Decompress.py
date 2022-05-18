#!/bin/python3
from typing import Generator
import logging
import os
from importlib import reload, import_module


class Decompress():
    # Still 2 things needs to be done:
    # 1. If libarchive not installed use building zip library
    # 2. If input file is and exe, try to seperate 7z file from PE part.
    libarchive = None

    @classmethod
    def setLibarchive(cls, lib_file: str = None) -> None:
        if lib_file:
            os.environ.update({"LIBARCHIVE": lib_file})

        if cls.libarchive:
            reload(cls.libarchive)
        else:
            cls.libarchive = import_module("libarchive")

    def __init__(self, filename: os.PathLike) -> None:
        if not self.libarchive:
            self.libarchive = import_module("libarchive")
        self.filename = filename
        self.filelist = list(self.getFileList())

    def getFileList(self) -> Generator:
        with self.libarchive.file_reader(self.filename) as archive:
            for entry in archive:
                yield str(entry)

    def getPrefixDir(self) -> str:
        if len(self.filelist) == 1:
            dir = ""
        else:
            dir = os.path.commonpath(self.filelist)
        return dir

    def extractFiles(self, filenames: list, outdir: os.PathLike) -> None:
        pwd_temp = os.getcwd()
        if not os.path.exists(outdir):
            os.makedirs(outdir)
        os.chdir(outdir)
        entries = self.select_entries_with_names(filenames)
        self.libarchive.extract.extract_entries(entries)
        os.chdir(pwd_temp)

    def select_entries_with_names(self, filenames: list) -> Generator:
        with self.libarchive.file_reader(self.filename) as archive:
            for entry in archive:
                if entry.name in filenames:
                    logging.debug("selected file '%s'" % entry.name)
                    yield entry

    def extractAll(self, outdir: os.PathLike) -> None:
        pwd_temp = os.getcwd()
        if not os.path.exists(outdir):
            os.makedirs(outdir)
        os.chdir(outdir)
        self.libarchive.extract_file(self.filename)
        os.chdir(pwd_temp)


if __name__ == "__main__":
    from _Log import my_log_settings
    my_log_settings()
    from _Aria2Rpc import Aria2Rpc
    a = Aria2Rpc(port=6801, passwd="abc", rpc_listen_all=True,
                 rpc_allow_origin_all=True, all_proxy="http://127.0.0.1:8123")
    temp_dir = "/mnt/temp"
    dl_urls = [
        "https://github.com/dezem/SAK/releases/download/0.7.14/SAK_v0.7.14_64bit_20220405-19-38-49.7z",
        "https://github.com/PDModdingCommunity/PD-Loader/releases/download/2.6.5a-r4n/PD-Loader-2.6.5a-r4.zip",
        "https://somesite/7z2107-x64.exe"
    ]
    for dl_url in dl_urls:
        download_file = os.path.join(temp_dir, os.path.basename(dl_url))

        if not os.path.exists(download_file):
            a.wget(dl_url, dir=temp_dir)

        try:
            f = Decompress(download_file)
            print(f.getPrefixDir())
        except Exception as e:
            logging.exception(e)

    a.quit()

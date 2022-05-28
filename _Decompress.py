#!/bin/python3
from typing import Generator
import logging
import os
from importlib import reload, import_module
from zipfile import ZipFile

class Decompress():
    # Still 2 things needs to be done:
    # 1. If libarchive not installed use build-in zip library
    # 2. If input file is and exe, try to seperate 7z file from PE part.
    try:
        libarchive = import_module("libarchive")
    except (ImportError, TypeError, OSError):
        libarchive = None

    @classmethod
    def setLibarchive(cls, lib_file: str) -> None:
        os.environ.update({"LIBARCHIVE": lib_file})
        if cls.libarchive:
            reload(cls.libarchive)
        else:
            cls.libarchive = import_module("libarchive")

    def __init__(self, filename: str, use_zipfile=False) -> None:
        self.filename = filename
        if not self.libarchive or use_zipfile:
            logging.warning(
                "using build-in ZipFile library on %s because libarchive is not available or user forcing" % filename)
            self.zf = ZipFile(self.filename)
            self.getFileList = self.zf.namelist
            self.extractAll = self.zf.extractall

            def extractFiles(filenames: list, outdir: str):
                for file in filenames:
                    self.zf.extract(file, outdir)
            self.extractFiles = extractFiles
            self.__del__ = self.zf.close
        elif filename.endswith(".exe"):
            logging.info("input an exe file, try extracting 7z sfx")
            self.reader = self.libarchive.memory_reader
            self.extracter = self.libarchive.extract_memory

            f = open(filename, "rb")
            while True:
                if f.read(8) == b'\x37\x7a\xbc\xaf\x27\x1c\x00\x04':
                    f.seek(-8, 1)
                    startof7z = f.tell()
                    logging.debug("found 7z header at 0x%x" % startof7z)
                    break
                else:
                    f.seek(-7, 1)
            self.read_from = f.read()
        else:
            self.reader = self.libarchive.file_reader
            self.extracter = self.libarchive.extract_file
            self.read_from = filename

    def getFileList(self) -> Generator:
        with self.reader(self.read_from) as archive:
            for entry in archive:
                if type(entry.name) == bytes:
                    logging.warning(
                        "none-ASCII character in filename '%s', this file will not be decompressed" % entry.name.decode(errors="ignore"))
                    continue
                yield entry.name

    def getPrefixDir(self) -> str:
        self.filelist = list(self.getFileList())
        if len(self.filelist) == 1:
            dir = ""
        else:
            dir = os.path.commonpath(self.filelist)
        return dir

    def extractFiles(self, filenames: list, outdir: str) -> None:
        pwd_temp = os.getcwd()
        if not os.path.exists(outdir):
            os.makedirs(outdir)
        os.chdir(outdir)
        entries = self.__select_entries_with_names(filenames)
        self.libarchive.extract.extract_entries(entries)
        os.chdir(pwd_temp)

    def __select_entries_with_names(self, filenames: list) -> Generator:
        with self.reader(self.read_from) as archive:
            for entry in archive:
                if entry.name in filenames:
                    logging.debug("selected file '%s'" % entry.name)
                    yield entry

    def extractAll(self, outdir: str) -> None:
        pwd_temp = os.getcwd()
        if not os.path.exists(outdir):
            os.makedirs(outdir)
        os.chdir(outdir)
        logging.debug("chdir to %s, starting extraction"%outdir)
        self.extracter(self.read_from)
        logging.debug("extraction complete")
        os.chdir(pwd_temp)


if __name__ == "__main__":
    from _Log import my_log_settings
    my_log_settings()
    from _Aria2Rpc import Aria2Rpc
    a = Aria2Rpc(port=6801, passwd="abc", rpc_listen_all=True,
                 rpc_allow_origin_all=True, split=16, max_connection_per_server=16, all_proxy="http://127.0.0.1:8123")
    temp_dir = "/mnt/temp/decompress"
    os.makedirs(temp_dir, exist_ok=True)
    dl_urls = [
        "https://github.com/dezem/SAK/releases/download/0.7.14/SAK_v0.7.14_64bit_20220405-19-38-49.7z",
        "https://github.com/PDModdingCommunity/PD-Loader/releases/download/2.6.5a-r4n/PD-Loader-2.6.5a-r4.zip",
        "https://www.7-zip.org/a/7z2107-x64.exe"
    ]
    import time
    import shutil
    for dl_url in dl_urls:
        download_file = os.path.join(temp_dir, os.path.basename(dl_url))

        if not os.path.exists(download_file) or os.path.exists(download_file+".aria2"):
            a.wget(dl_url, dir=temp_dir, retry=50)

        out_dir = os.path.basename(dl_url)+"_dir"
        out_dir = os.path.join(temp_dir, out_dir)

        shutil.rmtree(out_dir, ignore_errors=True)
        starttime = time.time()
        f = Decompress(download_file)
        f.extractAll(out_dir)
        time_used = time.time()-starttime
        logging.info("libarchive: %s" % time_used)

    a.quit()

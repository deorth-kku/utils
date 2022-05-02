#!/bin/python3
import subprocess
import os,sys
class Py7z: 
    bin_path="7z"
    @classmethod
    def set7zBin(cls,bin_path):
        cls.bin_path=bin_path
    def __init__(self, filename):
        if subprocess.call(self.bin_path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL):
            print("PLease check if 7z is installed")
            sys.exit(2)

        self.filename = filename

        self.getFileList()

    def getFileList(self):
        try:
            return self.filelist
        except AttributeError:
            self.filelist = []
            p=subprocess.Popen([self.bin_path, "l", self.filename], stdout=subprocess.PIPE, bufsize=1, universal_newlines=True)
            for line in p.stdout:
                line = line.split()
                if "....." in line or "....A" in line:
                    filename = line[-1]
                    self.filelist.append(filename)
            p.wait()
            if p.returncode!=0:
                raise FileBrokenError(self.filename)
            return self.filelist

    def getPrefixDir(self):
        if len(self.filelist)==1:
            dir=""
        else:
            dir = os.path.commonpath(self.filelist)
        return dir

    def extractFiles(self, filenames, outdir):
        cmd = [self.bin_path, "x", "-y", "-o"+outdir, self.filename]+filenames
        subprocess.call(cmd)

    def extractAll(self, outdir):
        cmd = [self.bin_path, "x", "-y", "-o"+outdir, self.filename]
        subprocess.call(cmd)


class FileBrokenError(Exception):
    def __init__(self, filename):
        Exception.__init__(self)
        self.message = "%s is not a correct compress file" % filename

    def __str__(self):
        return repr(self.message)

if __name__ == "__main__":
	pass

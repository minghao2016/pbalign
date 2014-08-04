#!/usr/bin/env python
###############################################################################
# Copyright (c) 2011-2013, Pacific Biosciences of California, Inc.
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# * Redistributions of source code must retain the above copyright
#   notice, this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
# * Neither the name of Pacific Biosciences nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
#
# NO EXPRESS OR IMPLIED LICENSES TO ANY PARTY'S PATENT RIGHTS ARE GRANTED BY
# THIS LICENSE.  THIS SOFTWARE IS PROVIDED BY PACIFIC BIOSCIENCES AND ITS
# CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT
# NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
# PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL PACIFIC BIOSCIENCES OR
# ITS CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
###############################################################################

# Author: Yuan Li

"""This scripts defines class TempFile and class TempFileManager for managing
temporary files and directories."""
from os import path, makedirs, remove, fdopen
import shutil
import logging
import tempfile
import time
from pbalign.utils.fileutil import isExist


class TempFile():
    """Class of temporary files and directories."""
    def __init__(self, name, own=False, isDir=False):
        """ Initialize a TempFile object.

        Set file name, indicate whether we own it or not.

        """
        self.name = name
        self.own = own
        self.isDir = isDir

    def __repr__(self):
        fileOrDir = "directory" if self.isDir else "file"
        return "TempFile({name}, {type}, own = {own})"\
               .format(name=self.name, type=fileOrDir,
                       own=('True' if self.own else 'False'))


class TempFileManager():
    """ Manage all temporary files and directories. """
    def __init__(self, rootDir=""):
        self.defaultRootDir = rootDir
        if (self.defaultRootDir != ""):
            self.defaultRootDir = path.abspath(path.expanduser(rootDir))
        self.fileDB = []
        self.dirDB = []
        self.SetRootDir(self.defaultRootDir)

    def __repr__(self):
        return "TempFileManager:\n" + \
               "   the default root dir is: {0}\n".\
               format(self.defaultRootDir) + \
               "   registered files are   : {0}\n".\
               format(",".join([obj.__repr__() for obj in self.fileDB])) + \
               "   registered folders are : {0}\n".\
               format(",".join([obj.__repr__() for obj in self.dirDB]))

    def SetRootDir(self, rootDir):
        """ Set default root directory for temporary files. """
        changeRootDir = True
        if (rootDir != ""):
            rootDir = path.abspath(path.expanduser(rootDir))
            if path.isdir(rootDir):
                # self.dirDB.append(TempFile(rootDir, own=False, isDir=True))
                # In case a dir (such as /scratch) is specified, create
                # another layer of sub-dir, and use it as the real rootDir.
                rootDir = tempfile.mkdtemp(dir=rootDir)
                self.dirDB.append(TempFile(rootDir, own=True, isDir=True))
                changeRootDir = False
            elif not isExist(rootDir):
                # Make the user-specified temporary directory.
                try:
                    makedirs(rootDir)
                    self.dirDB.append(TempFile(rootDir, own=True, isDir=True))
                    changeRootDir = False
                except (IOError, OSError):
                    # If fail to make the user-specified temp dir,
                    # create a new temp dir using tempfile.mkdtemp
                    changeRootDir = True

        if changeRootDir:
            try:
                rootDir = tempfile.mkdtemp()
                self.dirDB.append(TempFile(rootDir, own=True, isDir=True))
            except (IOError, OSError):
                # If fail to make temp dir
                rootDir = ""

        self.defaultRootDir = rootDir

    def _isRegistered(self, tempFileName):
        """ Is this a registered file or directory? """
        tempFileName = path.abspath(path.expanduser(tempFileName))
        if tempFileName in [obj.name for obj in self.fileDB] or \
           tempFileName in [obj.name for obj in self.dirDB]:
            return True
        else:
            return False

    def _RegisterTmpFile(self, tmpFile):
        """ Register a TmpFile obj. """
        if tmpFile.isDir:
            self.dirDB.append(tmpFile)
        else:
            self.fileDB.append(tmpFile)
        return tmpFile.name

    def RegisterNewTmpFile(self, isDir=False, rootDir="",
                           suffix="", prefix=""):
        """Create a new temporary file/directory under rootDir and
        register it in self.fileDB/self.dirDB. """
        if rootDir == "":
            if self.defaultRootDir == "":
                raise IOError("TempManager default root dir not set.")
            rootDir = self.defaultRootDir

        fileOrDir = "directory" if isDir else "file"
        thisPath = ""
        if isDir:
            thisPath = tempfile.mkdtemp(dir=rootDir,
                                        suffix=suffix,
                                        prefix=prefix)
        else:
            fHandler, thisPath = tempfile.mkstemp(dir=rootDir,
                                                  suffix=suffix,
                                                  prefix=prefix)
            f = fdopen(fHandler)
            f.close()

        thisPath = path.abspath(path.expanduser(thisPath))
        if self._isRegistered(thisPath):
            errMsg = "Failed to register a temporary {0} {1} twice.".\
                format(fileOrDir, thisPath)
            logging.error(errMsg)
            raise IOError(errMsg)

        return self._RegisterTmpFile(TempFile(thisPath, own=True, isDir=isDir))

    def RegisterExistingTmpFile(self, thisPath, own=False, isDir=False):
        """Register an existing temporary file/directory if it exists.
           Input:
                thisPath: path of the temporary file/directory to register.
                own     : Whether this object owns this file.
                isDir   : True = directory, False = file.
           Output:
                the abosolute expanded path of the input
        """
        errMsg = ""
        thisPath = path.abspath(path.expanduser(thisPath))
        fileOrDir = "directory" if isDir else "file"

        if not isDir and not isExist(thisPath):
            errMsg = "Failed to register a directory as a file."

        if isDir and not path.isdir(thisPath):
            errMsg = "Failied to register a file as a directory."

        if self._isRegistered(thisPath):
            errMsg = "Failed to register {0} {1} as it has been registered.".\
                format(fileOrDir, thisPath)

        if not isExist(thisPath):
            errMsg = "Failed to register {0} {1} as it does not exist.".\
                format(fileOrDir, thisPath)

        if errMsg != "":
            logging.error(errMsg)
            raise IOError(errMsg)

        return self._RegisterTmpFile(TempFile(thisPath,
                                              own=own, isDir=isDir))

    def CleanUp(self, realDelete=True):
        """Deregister all temporary files and directories, and delete them from
        the file system if realDelete is True.
        """
        # Always clean up temp files first.
        while len(self.fileDB) > 0:
            obj = self.fileDB.pop()
            if realDelete and obj.own and isExist(obj.name):
                logging.debug("Remove a temporary file {0}".format(obj.name))
                remove(obj.name)

        # Then clean up temp dirs
        while len(self.dirDB) > 0:
            obj = self.dirDB.pop()
            if realDelete and obj.own and isExist(obj.name):
                logging.debug("Remove a temporary dir {0}".format(obj.name))
                # bug 25074, in some systems occationally there might be a NFS
                # lock error: "Device or resource busy, unable to delete
                # .nfsxxxxxx".
                # This is because although all temp files have been deleted,
                # nfs still takes a while to send back an ack for the rpc call.
                # In that case, wait a few seconds before deleting the temp
                # directory, and try this several times.
                # If the temporary dir could not be deleted anyway, print a
                # warning instead of exiting with an error.
                times = 0
                maxTry = 5
                while times < maxTry:
                    try:
                        shutil.rmtree(obj.name)
                        break
                    except (IOError, OSError):
                        times += 1
                        # wait 3 seconds
                        time.sleep(3)
                if times >= maxTry:
                    logging.warn("Unable to remove a temporary dir {0}".
                                 format(obj.name))

        self.defaultRootDir = ""

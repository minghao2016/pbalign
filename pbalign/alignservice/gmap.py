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

"""This script defines class GMAPService which calls GMAP to align reads."""

# Author: Yuan Li

from __future__ import absolute_import
from os import path
from pbalign.alignservice.fastabasedalign import FastaBasedAlignService
from pbalign.utils.fileutil import isExist
from pbcore.util.Process import backticks
from time import sleep
from random import randint
import logging


class GMAPService(FastaBasedAlignService):
    """Class GMAPService calls gmap to align reads."""
    def __init__(self, options, fileNames, tempFileManager=None):
        super(GMAPService, self).__init__(options, fileNames, tempFileManager)
        self.dbRoot = None
        # If a GMAP DB is within a PacBio reference repository, its name should
        # always be 'gmap_db'. However, if it is not within a repository, its
        # name should be randomized. Otherwise, if multiple calls of
        # 'gmap_build' running simultaneously will fail.
        self.dbName = "gmap_db"

    @property
    def name(self):
        """GMAP Service name."""
        return "GMAPService"

    @property
    def progName(self):
        """Program to call."""
        return "gmap"

    @property
    def scoreSign(self):
        """Using edit distance as align score for GMAP, the lower the better.
        """
        return -1

    def _resolveAlgorithmOptions(self, options, fileNames):
        """ Resolve options specified within --algorithmOptions with
            options parsed from the command-line or the config file.
            Return updated options.
            If find conflicting values of the following options, error out.
               (1) --maxHits       and gmap -n
               (2) --maxAnchorSize and gmap -k
            Input:
                options  : the original pbalign options from argumentList
                           and configFile.
                fileNames: an PBAlignFiles object
            Output:
                new options by resolving options specified within
                --algorithmOptions and the original pbalign options
        """
        if options.algorithmOptions is None:
            return options

        unsupportedOptions = ['-1', '--selfalign', '-2', '--pairalign',
                              '--cmdline', '--cmetdir', '--atoidir',
                              '-v', '--use-snps',
                              '-V', '--snpsdir']
        # Ignore options to specify the input database
        ignoredBinaryOptions = ['-D', '-d']

        # Ignore options to specify output types, and always output in SAM
        # with full headers and the 'sam-use-0M' option.
        # Ignore --kmer, --nthreads, and --npaths
        # Ignore help and version.
        ignoredUnitaryOptions = ['-S', '-A', '-3', '-4', '-Z', '-E',
                                 '-P', '-Q', '-5', '--no-sam-headers',
                                 '-f', '--sam-use-0M', '--dir', '--db',
                                 '--kmer', '--nthreads', '--npaths',
                                 '--help', '--version']

        items = options.algorithmOptions.split(' ')
        i = 0
        try:
            while i < len(items):
                infoMsg, errMsg, item = "", "", items[i].split("=")[0]
                if item in unsupportedOptions:
                    raise ValueError("Unsupported option: {i}".format(i=item))
                elif item in ignoredUnitaryOptions:
                    infoMsg = "Ignore option: {i}".format(i=item)
                    del items[i:i+1]
                elif item in ignoredBinaryOptions:
                    infoMsg = "Ignore option: {i}".format(i=item)
                    del items[i:i+2]
                elif item == "-k":  # kmer size
                    val = int(items[i+1])
                    if options.minAnchorSize == val:
                        del items[i:i+2]
                    else:
                        errMsg = "Found conflicting options: " + \
                                 "--algorithmOptions '-k={k}'".format(k=val) +\
                                 "and --minAnchorSize={v}.".format(
                                     v=options.minAnchorSize)
                elif item == "-t":
                    val = int(items[i+1])
                    # The number of threads is not critical.
                    if options.nproc is None or \
                            int(options.nproc) != val:
                        infoMsg = "Over write nproc with {n}.".format(n=val)
                    options.nproc = val
                    del items[i:i+2]
                elif item == "-n":
                    val = int(items[i+1])
                    if options.maxHits == val:
                        del items[i:i+2]
                    else:
                        errMsg = "Found conflicting options: " + \
                            "--algorithmsOptions '-n={n}' and " + \
                            "--maxHits={v}.".format(v=options.maxHits)

                if errMsg != "":
                    logging.error(errMsg)
                    raise ValueError(errMsg)

                if infoMsg != "":
                    logging.info(self.name + ": Resolve algorithmOptions. " +
                                 infoMsg)

        except Exception as e:
            errMsg = "An error occured during parsing algorithmOptions " + \
                     "'{ao}': ".format(ao=options.algorithmOptions)
            logging.error(errMsg + str(e))
            raise ValueError(errMsg + str(e))

        # Update algorithmOptions when resolve is done
        options.algorithmOptions = " ".join(items)
        return options

    def _toCmd(self, options, fileNames, tempFileManager):
        """ Generate a command line for GMAP based on options and
            PBAlignFiles, and return a command-line string which can
            be used in bash.
            Input:
                options  : arguments parsed from the command-line, the
                           config file and --algorithmOptions.
                fileNames: an PBAlignFiles object.
                tempFileManager: temporary file manager.
            Output:
                a command-line string which can be used in bash.
        """
        cmdStr = "gmap -D {dbRoot} ".format(dbRoot=self.dbRoot) + \
                 "-d {dbName} -f samse ".format(dbName=self.dbName) + \
                 "--sam-use-0M {inFa} ".format(inFa=fileNames.queryFileName)

        if options.maxHits is not None and options.maxHits != "":
            cmdStr += "-n {n} ".format(n=options.maxHits)

        if (options.minAnchorSize is not None and
                options.minAnchorSize != ""):
            cmdStr += "-k {0} ".format(options.minAnchorSize)

        if options.nproc is not None and options.nproc != "":
            cmdStr += "-t {0} ".format(options.nproc)

        if options.algorithmOptions is not None:
            cmdStr += "{0} ".format(options.algorithmOptions)

        cmdStr += "> {outSam} ".format(outSam=fileNames.alignerSamOut)

        return cmdStr

    def _gmapCreateDB(self, referenceFile, isWithinRepository, tempRootDir):
        """
        Create gmap database for reference sequences if no DB exists.
        Wait for gmap DB to be created if gmap_db.lock exists.
        return (gmap_DB_root_path, gmap_DB_name).
        """
        # Determine dbRoot according to whether the reference file is wihtin
        # a reference repository.
        if isWithinRepository:
            # If the reference file is within a reference repository, create
            # gmap_db under the root of the repository, then the gmap DB root
            # is the repo root, and gmap DB name is 'gmap_db', e.g.,
            # refrepo/
            # --------sequence/
            # --------gmap_db/
            # --------reference.info.xml
            dbRoot = path.split(path.dirname(referenceFile))[0]
            dbName = "gmap_db"
        else: # Otherwise, create gmap_db under the tempRootDir, and give the
            # gmap DB a random name
            dbRoot = tempRootDir
            dbName = "gmap_db_{sfx}".format(sfx=randint(100000, 1000000))

        dbPath = path.join(dbRoot, dbName)
        dbLock = dbPath + ".lock"
        # Check if DB already exists
        if isExist(dbPath) and not isExist(dbLock):
            # gmap_db already exists
            logging.info(self.name + ": GMAP database {dbPath} found".format(
                         dbPath=dbPath))
            return (dbRoot, dbName)

        # Check if DB is being created by other pbalign calls
        while isExist(dbLock):
            logging.info(self.name + ": Waiting for GMAP database to be " + \
                         "created for {inFa}".format(inFa=referenceFile))
            sleep(10)

        # Create DB if it does not exist
        if not isExist(dbPath):
            # Touch the lock file
            _output, errCode, errMsg = backticks("touch {dbLock}".format(
                dbLock=dbLock))
            logging.debug(self.name + ": Create a lock when GMAP DB is " +
                          "being built.")
            if (errCode != 0):
                logging.error(self.name + ": Failed to create {dbLock}.\n" +
                              errMsg)
                backticks("rm -f {dbLock}".format(dbLock=dbLock))
                raise RuntimeError(errMsg)

            logging.info(self.name + ": Create GMAP DB for {inFa}.".format(
                inFa=referenceFile))
            cmdStr = "gmap_build -k 12 --db={dbName} --dir={dbRoot} {inFa}".\
                format(dbName=dbName, dbRoot=dbRoot, inFa=referenceFile)
            _output, errCode, errMsg = backticks(cmdStr)
            logging.debug(self.name + ": Call {cmdStr}".format(cmdStr=cmdStr))
            if (errCode != 0):
                logging.error(self.name + ": Failed to build GMAP db.\n" +
                              errMsg)
                backticks("rm -f {dbLock}".format(dbLock=dbLock))
                raise RuntimeError(errMsg)

            # Delete the lock file to notify others pbalign who are waiting
            # for this DB to be created.
            _output, errCode, errMsg = backticks("rm -f {dbLock}".format(
                dbLock=dbLock))
            logging.debug(self.name + ": Release the lock for DB creation.")
        return (dbRoot, dbName)

    def _preProcess(self, inputFileName, referenceFile, regionTable,
                    noSplitSubreads, tempFileManager, isWithinRepository):
        """Preprocess inputs and pre-build reference index files for gmap.

        For gmap, we need to
        (1) create indices for reference sequences,
        (2) convert the input PULSE/BASE/FOFN file to FASTA.
            Input:
                inputFileName  : a PacBio BASE/PULSE/FOFN file.
                referenceFile  : a FASTA reference file.
                regionTable    : a region table RGN.H5/FOFN file.
                noSplitSubreads: whether to split subreads or not.
                tempFileManager: temporary file manager.
            Output:
                String, a FASTA read file which can be used by gmap.
        """
        # Create a gmap database, update gmap DB root path and db name.
        (self.dbRoot, self.dbName) = self._gmapCreateDB(referenceFile,
                isWithinRepository, tempFileManager.defaultRootDir)

        # DO NOT delete gmap_db if it is within a reference repository;
        # otherwise, delete it.
        if not isWithinRepository:
            tempFileManager.RegisterExistingTmpFile(path.join(self.dbRoot,
                self.dbName), own=True, isDir=True)

        # Return a FASTA file that can be used by gmap as query directly.
        return self._pls2fasta(inputFileName, regionTable, noSplitSubreads)

    def _postProcess(self):
        """ Postprocess after alignment is done. """
        logging.debug(self.name + ": Postprocess after alignment is done. ")

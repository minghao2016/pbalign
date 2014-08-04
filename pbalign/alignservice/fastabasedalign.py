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

"""This script defines FastaBasedAlignService, a subclass of AlignService,
which converts PacBio reads in BASE/PULSE/FOFN formats into FASTA format before
align."""

# Author: Yuan Li
from __future__ import absolute_import
from pbalign.alignservice.align import AlignService
from pbalign.utils.fileutil import getFileFormat, FILE_FORMATS
from pbcore.util.Process import backticks
import logging


class FastaBasedAlignService(AlignService):
    """An abstract class for aligners that do not support PacBio reads in
    BASE/PULSE/FOFN formats. All subclasses need to call _pls2fasta in
    preprocess to convert input PacBio reads to FASTA."""

    def _pls2fasta(self, inputFileName, regionTable, noSplitSubreads):
        """ Call pls2fasta to convert a PacBio BASE/PULSe/FOFN file to FASTA.
            Input:
                inputFilieName : a PacBio BASE/PULSE/FOFN file.
                regionTable    : a region table RGN.H5/FOFN file.
                noSplitSubreads: whether to split subreads or not.
            Output:
                a FASTA file which can be used as an input by an aligner.
        """
        # If the incoming file is a FASTA file, no conversion is needed.
        if getFileFormat(inputFileName) == FILE_FORMATS.FASTA:
            return inputFileName

        # Otherwise, create a temporary FASTA file to write.
        outFastaFile = self._tempFileManager.RegisterNewTmpFile(
            suffix=".fasta")

        cmdStr = "pls2fasta {plsFile} {fastaFile} ".format(
            plsFile=inputFileName, fastaFile=outFastaFile)

        if regionTable is not None and regionTable != "":
            cmdStr += " -regionTable {rt} ".format(rt=regionTable)

        if noSplitSubreads:
            cmdStr += " -noSplitSubreads "

        logging.info(self.name + ": Convert {inFile} to FASTA format.".
                     format(inFile=inputFileName))
        logging.debug(self.name + ": Call \"{cmd}\"".format(cmd=cmdStr))

        _output, errCode, errMsg = backticks(cmdStr)
        if errCode != 0:
            errMsg += "Failed to convert {i} to {o}.".format(
                      i=inputFileName, o=outFastaFile)
            logging.error(errMsg)
            raise RuntimeError(errMsg)

        # Return the converted FASTA file which can be used by an aligner.
        return outFastaFile

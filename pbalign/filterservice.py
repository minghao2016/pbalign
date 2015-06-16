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

"""This script defines FilterService, which calls samFilter to remove aligments
in an input SAM file according to filtering criteria."""

# Author: Yuan Li

from __future__ import absolute_import
import logging
from pbalign.service import Service
from pbalign.utils.fileutil import getFileFormat, FILE_FORMATS, isExist

class FilterService(Service):
    """ Call samFilter to filter low quality hits and apply multiple hits
    policy. """
    @property
    def name(self):
        """Name of filter service."""
        return "FilterService"

    @property
    def progName(self):
        """Program to call."""
        return "samFilter"

    def __init__(self, inSamFile, refFile, outSamFile,
                 alignerName, scoreSign, options,
                 adapterGffFile=None):
        """Initialize a FilterService object.
            Input:
                inSamFile: an input SAM/BAM file
                refFile  : the reference FASTA file
                outSAM   : an output SAM/BAM file
                alnServiceName: the name of the align service
                scoreSign: score sign of the aligner, can be -1 or 1
                options  : pbalign options
                adapterGffFile: a GFF file storing all the adapters
        """
        self.inSamFile = inSamFile # sam|bam
        self.refFile = refFile
        self.outSamFile = outSamFile # sam|bam
        self.alignerName = alignerName
        self.scoreSign = scoreSign
        self.options = options
        self.adapterGffFile = adapterGffFile

    @property
    def cmd(self):
        """String of a command-line to execute."""
        return self._toCmd(self.inSamFile,  self.refFile,
                           self.outSamFile, self.alignerName,
                           self.scoreSign,  self.options,
                           self.adapterGffFile)

    def _toCmd(self, inSamFile, refFile, outSamFile,
            alignerName, scoreSign, options, adapterGffFile):
        """ Generate a samFilter command line from options.
            Input:
                inSamFile : the input SAM file
                refFile   : the reference FASTA file
                outSamFile: the output SAM file
                alignerName: aligner service name
                scoreSign : score sign, can be -1 or 1
                options   : argument options
            Output:
                a command-line string
        """
        # blasr supports in-line alignment filteration,
        # no need to call samFilter at all.
        if alignerName == "blasr" and \
            not self.options.filterAdapterOnly:
            cmdStr = "rm -f {outFile} && ln -s {inFile} {outFile}".format(
                    inFile=inSamFile, outFile=outSamFile)
            return cmdStr

        # if aligner is not blasr, call samFilter instead
        cmdStr = self.progName + \
            " {inSamFile} {refFile} {outSamFile} ".format(
                inSamFile=inSamFile,
                refFile=refFile,
                outSamFile=outSamFile)

        if options.maxDivergence is not None:
            maxDivergence = int(options.maxDivergence if options.maxDivergence
                                > 1.0 else (options.maxDivergence * 100))
            cmdStr += " -minPctSimilarity {0}".format(100 - maxDivergence)

        if options.minAccuracy is not None:
            minAccuracy = int(options.minAccuracy if options.minAccuracy > 1.0
                              else (options.minAccuracy * 100))
            cmdStr += " -minAccuracy {0}".format(minAccuracy)

        if options.minLength is not None:
            cmdStr += " -minLength {0}".format(options.minLength)

        if options.seed is not None:
            cmdStr += " -seed {0}".format(options.seed)

        if scoreSign in [1, -1]:
            cmdStr += " -scoreSign {0}".format(scoreSign)
        else:
            logging.error("{0}'s score sign is neither 1 nor -1.".format(
                alignerName))

        if options.scoreCutoff is not None:
            cmdStr += " -scoreCutoff {0}".format(options.scoreCutoff)

        if options.hitPolicy is not None:
            cmdStr += " -hitPolicy {0}".format(options.hitPolicy)

        if options.filterAdapterOnly is True and \
            isExist(adapterGffFile):
            cmdStr += " -filterAdapterOnly {gffFile}".format(
                    gffFile=adapterGffFile)

        return cmdStr

    def run(self):
        """ Run the filter service. """
        logging.info(self.name + ": Filter alignments using {0}.".
                     format(self.progName))
        return self._execute()

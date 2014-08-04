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
"""This script defines class PBALignFiles."""

from __future__ import absolute_import
import logging
from pbalign.utils.fileutil import checkInputFile, getRealFileFormat, \
    checkOutputFile, checkReferencePath, checkRegionTableFile, \
    getFileFormat, FILE_FORMATS


class PBAlignFiles:
    """PBAlignFiles contains files that will be used by pbalign."""
    def __init__(self, inputFileName=None, referencePath=None,
                 outputFileName=None, regionTable=None,
                 pulseFileName=None):
        """ Initialize an instance of PBAlignFiles.
        Input:
            inputFileName : The user-specified input PacBio read file
                            can be in FASTA/BASE/PULSE/FOFN format.
            referencePath : The user-specified reference path or file.
            outputFileName: The user-specified output file in CMP.H5 or
                            SAM format.
            regionTable   : The user-specified region table. It can
                            be None if region table is not specified.
        """
        self.inputFileName = None   # The input PacBio read files.
        self.referencePath = None   # The reference file or repository.
        self.outputFileName = None  # The output CMP.H5 or SAM file.
        self.regionTable = None     # The region table.

        # The query file that will be used by an aligner. queryFileName
        # and inputFileName can be different, because PacBio BASE/PULSE/FOFN
        # files need to be converted to FASTA for aligners that do not accept
        # PacBio reads.
        self.queryFileName = None

        # Load pulses from the pulse file. When input reads are in
        # BASE/PULSE/CCS.H5 files, pulseFileName=inputFileName;
        # otherwise, use '--pulseFile'.
        self.pulseFileName = None

        # File format of inputFileName if it is not a FOFN; otherwise,
        # file format of the first file in FOFN: FASTA/BAS.H5/PLS.H5/CCS.H5.
        self.inputFileFormat = None

        # The target (reference) file that will be used by an aligner.
        # referencePath can be a directory but targetFileName should always
        # be a FASTA file.
        self.targetFileName = None
        self.sawriterFileName = None
        self.isWithinRepository = False
        self.alignerSamOut = None   # The sam output file by an aligner
        self.filteredSam = None     # The filtered sam file.

        # There might be an adapter file in the reference repository in
        # directory 'annotations', which can be used by the
        # 11k_Unrolled_Resequencing protocol to filter reads that
        # only map to adapter regions.
        self.adapterGffFileName = None

        # Verify and assign the input & output files.
        self.SetInOutFiles(inputFileName, referencePath,
                           outputFileName, regionTable, pulseFileName)

    def SetInputFile(self, inputFileName):
        """Verify and assign input file name and input file format."""
        # Validate the user-specified input PacBio read file and get
        # the absolute and expanded path. Validate file format.
        if inputFileName is not None and inputFileName != "":
            self.inputFileName = checkInputFile(inputFileName)
            self.inputFileFormat = getRealFileFormat(inputFileName)

    def SetPulseFileName(self, inputFileName, pulseFileName):
        """Verify and assign the pulse file from which pulses can be
        extracted. When inputFileName is a Base/Pulse/CCS.H5 file or a
        fofn of Base/Pulse/CCS.H5, pulse file is inputFileName. Otherwise,
        pulse file is pulseFileName."""
        self.pulseFileName = None
        if inputFileName is not None and inputFileName != "":
            inputFormat = getRealFileFormat(inputFileName)
            if inputFormat in [FILE_FORMATS.BAS, FILE_FORMATS.BAX,
                    FILE_FORMATS.PLS, FILE_FORMATS.PLX, FILE_FORMATS.CCS]:
                self.pulseFileName = checkInputFile(inputFileName)

        if self.pulseFileName is None:
            if pulseFileName is not None and pulseFileName != "":
                self.pulseFileName = checkInputFile(pulseFileName)

    def SetReferencePath(self, referencePath):
        """Validate the user-specified referencePath and get the absolute
        and expanded path for referencePath, targetFileName and
        sawriterFileName. targetFileName is the target reference FASTA
        file to be used by an aligner. sawriterFileName is the reference
        sawriter file that can be used by an aligner (e.g. blasr), its
        value can be None if absent.
        """
        if referencePath is not None and referencePath != "":
            (self.referencePath, self.targetFileName,
             self.sawriterFileName, self.isWithinRepository,
             self.adapterGffFileName) = \
            checkReferencePath(referencePath)

    def SetOutputFileName(self, outputFileName):
        """Validate the user-specified output file and get the absolute and
        expanded path.
        """
        if outputFileName is not None and outputFileName != "":
            self.outputFileName = checkOutputFile(outputFileName)

    def SetRegionTable(self, regionTable):
        """Validate the user-specified region table and get the absolute and
        expanded path. The value can be None if regionTable is not given.
        """
        if regionTable is not None and regionTable != "":
            self.regionTable = checkRegionTableFile(regionTable)

    def SetInOutFiles(self, inputFileName, referencePath,
                      outputFileName, regionTable, pulseFileName=None):
        """Verify and assign the input & output files."""
        self.SetInputFile(inputFileName)

        self.SetReferencePath(referencePath)

        self.SetOutputFileName(outputFileName)

        self.SetRegionTable(regionTable)

        self.SetPulseFileName(inputFileName, pulseFileName)

    def __repr__(self):
        """ Represent PBAlignFiles."""
        desc = "Input file : {i}\n".format(i=self.inputFileName)
        desc += "Reference path: {r} ".format(r=self.referencePath)
        desc += "is {res}within a reference repository.\n".format(
                res="" if self.isWithinRepository else "not ")
        desc += "Output file: {o}\n".format(o=self.outputFileName)
        desc += "Query file : {q}\n".format(q=self.queryFileName)
        desc += "Target file: {t}\n".format(t=self.targetFileName)
        desc += "Suffix array file: {s}\n".format(s=self.sawriterFileName)
        desc += "regionTable:{s}\n".format(s=self.regionTable)
        if self.pulseFileName is not None:
            desc += "Pulse files: {s}\n".format(s=self.pulseFileName)
        desc += "Aligner's SAM out: {t}\n".format(t=self.alignerSamOut)
        desc += "Filtered SAM file: {t}\n".format(t=self.filteredSam)
        if self.adapterGffFileName is not None:
            desc += "Adapter GFF file: {t}\n".format(
                t=self.adapterGffFileName)
        return desc

#if __name__ == "__main__":
#    p = PBAlignFiles("lambda.fasta", "lambda_ref.fasta", "tmp.sam")

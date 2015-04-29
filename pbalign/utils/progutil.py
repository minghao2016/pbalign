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

"""This script defines faciliating functions for calling programs."""

# Author: Yuan Li

from __future__ import absolute_import
from pbcore.util.Process import backticks
import logging


def Availability(progName):
    """Return True if a program is available, otherwise false."""
    return (backticks("which {0}".format(progName))[1] == 0)


def CheckAvailability(progName):
    """Raise a runtime error if a program is not available."""
    if not Availability(progName):
        raise RuntimeError("{0} is not available.".format(progName))


def Execute(name, cmd):
    """Execute the sepcified command in bash.
    Raise a RuntimeError if execution of cmd fail.

    Input:
        cmd: a command-line string to execute in bash
    Output:
        output : the cmd output
        errCode: the error code (zero means normal exit)
        errMsg : the error message
    """
    logging.info(name + ": Call \"{0}\"".format(cmd))
    output, errCode, errMsg = backticks(cmd)
    if errCode != 0:
        errMsg = name + " returned a non-zero exit status. " + errMsg
        logging.error(errMsg)
        raise RuntimeError(errMsg)
    return output, errCode, errMsg

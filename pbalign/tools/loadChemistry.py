#!/usr/bin/env python

USAGE = \
"""
loadChemistry.py

 Load chemistry info into a cmp.h5, just copying the triple.  Note
 that there is no attempt to "decode" chemistry barcodes here---this
 is a dumb pipe.

 usage:
  % loadChemistry [input.fofn | list of input.ba[sx].h5] aligned_reads.cmp.h5
"""

import sys, h5py, numpy as np
from pbcore.io import *

class ChemistryLoadingException(BaseException): pass

STRING_DTYPE = h5py.special_dtype(vlen=bytes)

def safeDelete(group, dsName):
    if dsName in group:
        del group[dsName]

def writeTriples(movieInfoGroup, triplesByMovieName):
    movieNamesInCmpH5 = list(movieInfoGroup["Name"])
    if not set(movieNamesInCmpH5).issubset(set(triplesByMovieName.keys())):
        raise ChemistryLoadingException, "Mismatch between movies in input.fofn and cmp.h5 movies"

    safeDelete(movieInfoGroup, "BindingKit")
    safeDelete(movieInfoGroup, "SequencingKit")
    safeDelete(movieInfoGroup, "SoftwareVersion")

    shape = movieInfoGroup["Name"].shape
    bindingKit      = movieInfoGroup.create_dataset("BindingKit"     , shape=shape, dtype=STRING_DTYPE, maxshape=(None,))
    sequencingKit   = movieInfoGroup.create_dataset("SequencingKit"  , shape=shape, dtype=STRING_DTYPE, maxshape=(None,))
    softwareVersion = movieInfoGroup.create_dataset("SoftwareVersion", shape=shape, dtype=STRING_DTYPE, maxshape=(None,))

    for (movieName, triple) in triplesByMovieName.items():
        if movieName in movieNamesInCmpH5:
            idx = movieNamesInCmpH5.index(movieName)
            bindingKit[idx]      = triple[0]
            sequencingKit[idx]   = triple[1]
            softwareVersion[idx] = triple[2]

    assert all(bindingKit.value      != "")
    assert all(sequencingKit.value   != "")
    assert all(softwareVersion.value != "")


def main():
    if len(sys.argv) < 3:
        print USAGE
        return -1

    inputFilenames = sys.argv[1:-1]
    cmpFname = sys.argv[-1]

    if len(inputFilenames) == 1 and inputFilenames[0].endswith(".fofn"):
        basFnames = list(enumeratePulseFiles(inputFilenames[0]))
    else:
        basFnames = inputFilenames

    f = h5py.File(cmpFname, "r+")
    movieInfoGroup = f["MovieInfo"]

    triples = {}
    for basFname in basFnames:
        bas = BasH5Reader(basFname)
        movieName = bas.movieName
        chemTriple = bas.chemistryBarcodeTriple
        triples[movieName] = chemTriple

    writeTriples(movieInfoGroup, triples)

if __name__ == '__main__':
    main()

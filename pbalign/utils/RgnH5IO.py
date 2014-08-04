#!/usr/bin/env python
# Author: Yuan Li
"""
Region table reader and writer.
"""
__all__ = ["RgnH5Reader",
           "RgnH5Writer"]
import h5py
import os.path as op
import numpy as np
from pbcore.io.BasH5IO import ADAPTER_REGION, INSERT_REGION, HQ_REGION, \
    REGION_TABLE_DTYPE, toRecArray, _makeRegionTableIndex

__version__ = "1.0"
REGION_COLUMN_NAMES = (
    "HoleNumber",
    "TypeIndex",
    "Start",
    "End",
    "Score"
    )
REGION_TYPES = (
    "Adapter",
    "Insert",
    "HQRegion"
    )
REGION_SOURCES = (
    "AdapterFinding",
    "AdapterFinding",
    "PulseToBase Region classifer"
    )
REGION_DESCRIPTIONS = (
    "Adapter Hit", "Insert Region",
    "High Quality bases region. Score is 1000 * predicted accuracy, " +
    "where predicted accuary is 0 to 1.0"
    )


class Region(object):
    """
    A `Region` represents a row in /PulseData/Regions, including five fields:
    HoleNumber, TypeIndex, Start, End and Score.
    """
    __slots__ = ['holeNumber', 'typeIndex', 'start', 'end', 'score']

    def __init__(self, l):
        self.holeNumber = np.int32(l[0])
        self.typeIndex = np.int32(l[1])
        self.start = np.int32(l[2])
        self.end = np.int32(l[3])
        self.score = np.int32(l[4])

    def __repr__(self):
        return "ZMW=%r, %r, start=%r, end=%r, score=%r\n" % (
            self.holeNumber, REGION_TYPES[self.typeIndex],
            self.start, self.end, self.score)

    def toTuple(self):
        """Convert a Region object to a tuple."""
        return (self.holeNumber, self.typeIndex,
                self.start, self.end, self.score)

    def setStartAndEnd(self, newStart, newEnd):
        """Reset start and end."""
        self.start = newStart
        self.end = newEnd

    @property
    def isHqRegion(self):
        """Is this a HQ region?"""
        return self.typeIndex == HQ_REGION

    @property
    def isAdapter(self):
        """Is this an adapter?"""
        return self.typeIndex == ADAPTER_REGION

    @property
    def isInsert(self):
        """Is this an insert region?"""
        return self.typeIndex == INSERT_REGION


class RegionTable(object):
    """
    A `RegionTable` represents a list of all regions of a ZMW.
    """

    def __init__(self, holeNumber, regions):
        self.holeNumber = holeNumber
        for r in regions:
            assert self.holeNumber == r.holeNumber, \
                "RegionTable instantiated with holeNumber %i != " \
                "region holeNumber %i" % (self.holeNumber, r.holeNumber)
        self.regions = regions

    def __str__(self):
        ret = "ZMW: %s, regions are:\n" % self.holeNumber
        for r in self.regions:
            ret += "  (%s, %s, %s, %s)" % (REGION_TYPES[r.typeIndex],
                                           r.start, r.end, r.score)
        return ret

    def setHQRegion(self, newHQStart, newHQEnd):
        """
        If a HQ region exists, reset HQ region; otherwise add one.
        """
        hqRegionsFound = 0
        for r in self.regions:
            if r.isHqRegion:
                r.setStartAndEnd(newHQStart, newHQEnd)
                hqRegionsFound += 1
        if hqRegionsFound == 0:
            # No HQ Region exists in the region table, add one to the table.
            self.regions.append(
                Region([self.holeNumber, HQ_REGION, newHQStart, newHQEnd, 0]))
        elif hqRegionsFound > 1:
            # If more than one HQ region exists, give a warning.
            print "WARNING: Found more than one HQ region in ZMW %s." % \
                self.holeNumber

    def __len__(self):
        return self.regions.__len__()

    def __getitem__(self, key):
        return self.regions.__getitem__(key)

    def __delitem__(self, key):
        return self.regions.__delitem__(key)

    def __setitem__(self, key, value):
        return self.regions.__setitem__(key, value)

    @property
    def numRegions(self):
        """Return the number of regions in a ZMW's region table."""
        return len(self.regions)

    def toList(self):
        """Return a list of regions."""
        return [r.toTuple() for r in self.regions]


class RgnH5Reader(object):
    """
    The `RgnH5Reader` class provides access to rgn.h5 files.

    Region tables are usually small (e.g. a few MB), so we can cache all data.

    To use RgnH5Reader and RgnH5Writer:
        reader = RgnH5Reader(inFileName)
        writer = RgnH5Reader(outFileName)
        writer.writeScanDataGroup(reader.scanDataGroup)
        for rt in reader:
            writer.addRegionTable(rt)
        reader.close()
        writer.close()
    """

    def __init__(self, filename):
        self.filename = op.abspath(op.expanduser(filename))
        self.file = h5py.File(self.filename, 'r')
        if "Regions" in self.file["/PulseData"]:
            self._regionsGroup = self.file["/PulseData/Regions"]
        else:
            raise TypeError("Unsupported region table which does not " +
                            "contain /PulseData/Regions: %s " % self.filename)
        self._regionsData = toRecArray(
            REGION_TABLE_DTYPE, self._regionsGroup.value)

        self._regionTableIndex = _makeRegionTableIndex(
            self._regionsData.holeNumber)
        self.holeNumbers = set(self._regionsData.holeNumber)

    def __iter__(self):
        for holeNumber in self.holeNumbers:
            startRow, endRow = self._regionTableIndex[holeNumber]
            yield RegionTable(
                holeNumber,
                [Region(r) for r in self._regionsData[startRow:endRow]])

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    @property
    def movieName(self):
        """Copied from BasH5Reader, written by David Alexander."""
        movieNameAttr = self.file["/ScanData/RunInfo"].attrs["MovieName"]

        # In old bas.h5 files, attributes of ScanData/RunInfo are stored as
        # strings in arrays of length one.
        if (isinstance(movieNameAttr, (np.ndarray, list)) and
                len(movieNameAttr) == 1):
            movieNameString = movieNameAttr[0]
        else:
            movieNameString = movieNameAttr

        if not isinstance(movieNameString, basestring):
            raise TypeError("Unsupported movieName {m} of type {t}."
                            .format(m=movieNameString,
                                    t=type(movieNameString)))
        return movieNameString

    @property
    def numZMWs(self):
        """Return the number of ZMWs in the region table."""
        return len(self.holeNumbers)

    @property
    def scanDataGroup(self):
        """Return /ScanData Group."""
        return self.file["/ScanData"]

    def close(self):
        """Close the file."""
        if hasattr(self, "file") and self.file is not None:
            self.file.close()
            self.file = None


def addStrListAttr(obj, attrName, attrList):
    """Add a string list as an attribute to a hdf5 object."""
    obj.attrs[attrName] = np.array(attrList, dtype=h5py.new_vlen(str))


class RgnH5Writer(object):
    """Region table writer."""

    def __init__(self, filename):
        self.filename = op.abspath(op.expanduser(filename))
        if not self.filename.endswith("rgn.h5"):
            raise TypeError("File extension of region table: " +
                            "%s should be rgn.h5" % self.filename)
        self.file = h5py.File(self.filename, 'w')
        self.regions = []

    def _addVersion(self):
        """Add version to file."""
        self.file.attrs['Version'] = __version__

    def _addRegionsDataset(self):
        """Add /PulseData/Regions dataset."""
        # Create /PulseData group.
        pulseDataGroup = self.file.create_group("PulseData")
        # Get the total number of regions in region table.
        numRegions = len(self.regions)
        shape = (max(1, numRegions), len(REGION_COLUMN_NAMES))
        # Add /PulseData/Regions dataset.
        # The datatype is int32 instead of uint32 because scores can be -1.
        regionsDataset = pulseDataGroup.create_dataset(
            "Regions", shape, np.int32,
            maxshape=(None, len(REGION_COLUMN_NAMES)))
        # Add attributes to Regions.
        addStrListAttr(regionsDataset, "ColumnNames", REGION_COLUMN_NAMES)
        addStrListAttr(regionsDataset, "RegionTypes", REGION_TYPES)
        addStrListAttr(regionsDataset, "RegionDescriptions",
                       REGION_DESCRIPTIONS)
        addStrListAttr(regionsDataset, "RegionSources", REGION_SOURCES)

        # Fill Regions dataset.
        if len(self.regions) == 0:
            self.regions = [(0, 0, 0, 0, 0)]
        regionsDataset[:] = np.array(self.regions)

    def writeScanDataGroup(self, scanDataGroup=None):
        """Copy /ScanData group if not None."""
        if scanDataGroup is not None:
            self.file.copy(scanDataGroup, "/ScanData")

    def addRegionTable(self, regionTable):
        """Add a ZMW's region table to the writer's region table list."""
        self.regions.extend(regionTable.toList())

    def write(self):
        """Write the region table list to file."""
        # ensure the output is sorted by hole number, de facto "spec" for rgn.h5
        self.regions.sort(key=lambda x:x[0])
        self._addVersion()
        self._addRegionsDataset()

    def close(self):
        """Close the file."""
        if hasattr(self, "file") and self.file is not None:
            self.write()
            self.file.close()
            self.file = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

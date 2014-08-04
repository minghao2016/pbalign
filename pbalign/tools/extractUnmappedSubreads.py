#!/usr/bin/env python
"""
Starts with the filtered_reads.fa file. Reads in the control.cmp.h5 and
reference.cmp.h5, removing any subreads that map. Writes resulting fasta
entries to stdout.
"""

import sys
import logging
import os.path as op
import re
import h5py
from pbcore.io import FastaReader
from pbcore.util.ToolRunner import PBToolRunner

__version__ = "0.1.0.133504"


class ExtractRunner(PBToolRunner):
    """ExtractUnmappedReads Runner."""
    def __init__(self):
        """Handle command line argument parsing"""
        desc = "Extract unmapped subreads from a fasta file."
        PBToolRunner.__init__(self, desc)
        self.set_parser(self.parser)
        self.fastaFN = None
        self.cmpH5FNs = []

    def set_parser(self, parser):
        """Set parser."""
        parser.add_argument("fasta", type=str,
                            help="a fasta file containing all subreads.")
        parser.add_argument("cmph5", metavar="cmp.h5", nargs="+",
                            help="input cmp.h5 files.")
        return parser

    def getVersion(self):
        """Get version string."""
        return __version__

    def _getFastaReadsInfo(self, fastaReads):
        """ Get reads' info (not including alignments) from the fasta. """
        pattern = re.compile(r"(m.+)\/(\d+)\/(\d+)_(\d+)")
        #for entry in FastaIO.SimpleFastaReader(self.fastaFN):
        with FastaReader(self.fastaFN) as reader:
            for entry in reader:
                match = pattern.search( entry.name.strip() )
                if not match:
                    continue
                movie, holeNumber, srStart, srEnd = match.groups()
                holeNumber, srStart, srEnd = \
                    int(holeNumber), int(srStart), int(srEnd)
                fastaReads.setdefault(movie, {})
                fastaReads[movie].setdefault(holeNumber, [])
                fastaReads[movie][holeNumber].append((srStart, srEnd))

    def _loadMappedSubreads(self, subreads, cmpH5FN):
        """Loads all subreads from the specified cmpH5 into the
        subread data structure."""
        cmpFile = h5py.File(cmpH5FN, 'r')
        movieInfo = cmpFile["/MovieInfo"]
        movieDict = dict(zip(movieInfo["ID"], movieInfo["Name"]))

        numAln = cmpFile["/AlnInfo/AlnIndex"].shape[0]
        movieIdIdx, holeIdx, startIdx, endIdx = 2, 7, 11, 12

        if numAln != 0:
            for row in cmpFile["/AlnInfo/AlnIndex"].value:
                movie = movieDict[row[movieIdIdx]]
                subreads.setdefault(movie, {})
                subreads[movie].setdefault(row[holeIdx], [])
                subreads[movie][row[holeIdx]].append(
                    (row[startIdx], row[endIdx]))
        logging.info("Loaded {n} subreads from {f}".format(n=numAln, f=cmpH5FN))
        cmpFile.close()

    def _rmMappedReads( self, fastaReadsPos, cmpReadsPos):
        """ Remove fasta reads that are mapped. """
        # For a read of a hole, the number of subreads that can map to reference
        # is usually small (e.g. 1 or 2). Actually, it is not profitable at all
        # to "sort and binary search for mapped subreads" based on experiments.
        i = 0
        while i < len(fastaReadsPos):
            fStart, fEnd = fastaReadsPos[i]
            for cStart, cEnd in cmpReadsPos:
                if cStart >= fStart and cEnd <= fEnd:
                    logging.debug("{0} {1} in {2} {3} ?".\
                        format(cStart, cEnd, fStart, fEnd))
                    fastaReadsPos.pop(i)
                    i -= 1
                    break
            i += 1

    def _printUnMappedReads(self, fastaReads):
        """Print unmapped subreads."""
        pattern = re.compile(r"(m.+)\/(\d+)\/(\d+)_(\d+)")
        with FastaReader(self.fastaFN) as reader:
            for entry in reader:
                match = pattern.search( entry.name.strip() )
                if not match:
                    continue
                movie, holeNumber, srStart, srEnd = match.groups()
                holeNumber, srStart, srEnd = \
                    int(holeNumber), int(srStart), int(srEnd)
                if movie in fastaReads and \
                   holeNumber in fastaReads[movie] and \
                   (srStart, srEnd) in fastaReads[movie][holeNumber]:
                    entry.COLUMNS=70
                    print str(entry)

    def run(self):
        """Executes the body of the script."""
        logging.info("Running {f} v{v}.".format(f=op.basename(__file__),
                                                v=self.getVersion))
        args = self.args
        logging.info("Extracting unmapped reads from a fasta file.")

        self.fastaFN = args.fasta
        self.cmpH5FNs = args.cmph5
        logging.debug("Input fasta is {f}.".format(f=self.fastaFN))
        logging.debug("Input fasta is {f}.".format(f=self.cmpH5FNs))

        fastaReads = {}
        self._getFastaReadsInfo(fastaReads)

        subreads = {}
        for cmpH5FN in self.cmpH5FNs:
            subreads = { }
            self._loadMappedSubreads(subreads, cmpH5FN)

            for movie in subreads:
                for holeNumber in subreads[movie]:
                    logging.debug("Movie: {m}".format(m=movie))
                    if movie not in fastaReads:
                        break
                    elif holeNumber not in fastaReads[movie]:
                        continue
                    # Remove mapped reads from fastaReads[movie][holeNumber]
                    self._rmMappedReads(fastaReads[movie][holeNumber],
                                        subreads[movie][holeNumber])

        # Print unmapped reads
        self._printUnMappedReads(fastaReads)


#   The following code can cut the memory used in half (if there is only
#   one cmpH5FN) at the expense of increased running time
#   (by 80% ~ 100% if there are multiple movies).
#   def run( self ):
#        """Executes the body of the script."""
#
#        logging.info("Log level set to INFO")
#        logging.debug("Log Level set to DEBUG")
#
#        subreads = { }
#        for cmpH5FN in self.cmpH5FNs:
#            self._loadMappedSubreads( subreads, cmpH5FN )
#
#        subreadId = re.compile("(m.+)\/(\d+)\/(\d+)_(\d+)")
#        for entry in FastaIO.SimpleFastaReader( self.fastaFN ):
#            match = subreadId.search( entry.name.strip() )
#            if not match:
#                continue
#            movie, read, srStart, srEnd = [match.group(i) for i in range(1,5)]
#            read, srStart, srEnd = int(read), int(srStart), int(srEnd)
#            mapped = False
#            if movie in subreads and read in subreads[ movie ]:
#                ids = subreads[ movie ][ read ]
#                logging.debug("Movie: %s" % movie)
#                for id in ids:
#                    logging.debug("%s inside %s?" %
#                                  ( str(id), "(%s,%s)" % ( srStart, srEnd)))
#                    if id[0] >= srStart and id[1] <= srEnd:
#                        mapped = True
#                        break
#            if not mapped:
#                print str(entry)
#
#        return 0

def main():
    """Main entry"""
    runner = ExtractRunner()
    return runner.start()


if __name__ == "__main__":
    sys.exit(main())

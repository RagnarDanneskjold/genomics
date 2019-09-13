#!/usr/bin/env python
#
#     fastq_strand.py: determine strandedness of fastq pair using STAR
#     Copyright (C) University of Manchester 2017-2019 Peter Briggs
#

__version__ = "0.0.7"

#######################################################################
# Imports
#######################################################################

from builtins import str
import sys
import os
import io
import argparse
import tempfile
import random
import subprocess
import shutil
import logging
from bcftbx.utils import find_program
from bcftbx.ngsutils import getreads
from bcftbx.ngsutils import getreads_subset
from bcftbx.qc.report import strip_ngs_extensions
from builtins import range

#######################################################################
# Tests
#######################################################################

import unittest

fq_r1_data = u"""@K00311:43:HL3LWBBXX:8:1101:21440:1121 1:N:0:CNATGT
GCCNGACAGCAGAAATGGAATGCGGACCCCTTCNACCACCANAATATTCTTNATNTTGGGTNTTGCNAANGTCTTC
+
AAF#FJJJJJJJJJJJJJJJJJJJJJJJJJJJJ#JJJJJJJ#JJJJJJJJJ#JJ#JJJJJJ#JJJJ#JJ#JJJJJJ
@K00311:43:HL3LWBBXX:8:1101:21460:1121 1:N:0:CNATGT
GGGNGTCATTGATCATTTCTTCAGTCATTTCCANTTTCATGNTTTCCTTCTNGANATTCTGNATTGNTTNTAGTGT
+
AAF#FJJJJJJJJJJJJJJJJJJJJJJJJJJJJ#JJJJJJJ#JJJJJJJJJ#JJ#JJJJJJ#JJJJ#JJ#JJJJJJ
@K00311:43:HL3LWBBXX:8:1101:21805:1121 1:N:0:CNATGT
CCCNACCCTTGCCTACCCACCATACCAAGTGCTNGGATTACNGGCATGTATNGCNGCGTCCNGCTTNAANTTAA
+
AAF#FJJJJJJJJJJJJJJJJJJJJJJJJJJJJ#JJJJJJJ#JJJJJJJJJ#JJ#JJJAJJ#JJJJ#JJ#JJJJ
"""
fq_r2_data = u"""@K00311:43:HL3LWBBXX:8:1101:21440:1121 2:N:0:CNATGT
CAANANGGNNTCNCNGNTNTNCTNTNAGANCNNTGANCNGTTCTTCCCANCTGCACTCTGCCCCAGCTGTCCAGNC
+
AAF#F#JJ##JJ#J#J#J#J#JJ#J#JJJ#J##JJJ#J#JJJJJJJJJJ#JJJJJJJJJJJJJJJJJJJJJJJJ#J
@K00311:43:HL3LWBBXX:8:1101:21460:1121 2:N:0:CNATGT
ATANGNAANNGTNCNGNGNTNTANCNAAGNANNTTGNCNACCTACGGAAACAGAAGACAAGAACGTTCGCTGTA
+
AAF#F#JJ##JJ#J#J#J#J#JJ#J#JJJ#J##JJJ#J#JJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJ
@K00311:43:HL3LWBBXX:8:1101:21805:1121 2:N:0:CNATGT
GAANANGCNNACNGNGNTNANTGNTNATGNANNTAGNGNTTCTCTCTGAGGTGACAGAAATACTTTAAATTTAANC
+
AAF#F#JJ##JJ#J#J#J#J#JJ#J#JJJ#F##JJJ#J#JJJJJJFAJJJJFJJJJJJJJJJJJJJJJJFFFJJ#J
"""

def mockSTAR(argv,unmapped_output=False):
    # Implements a "fake" STAR executable which produces
    # a single output (ReadsPerGene.out.tab file)
    p = argparse.ArgumentParser()
    p.add_argument('--runMode',action="store")
    p.add_argument('--genomeLoad',action="store")
    p.add_argument('--genomeDir',action="store")
    p.add_argument('--readFilesIn',action="store",nargs='+')
    p.add_argument('--quantMode',action="store")
    p.add_argument('--outSAMtype',action="store",nargs=2)
    p.add_argument('--outSAMstrandField',action="store")
    p.add_argument('--outFileNamePrefix',action="store",dest='prefix')
    p.add_argument('--runThreadN',action="store")
    args = p.parse_args(argv)
    with io.open("%sReadsPerGene.out.tab" % args.prefix,'wt') as fp:
        if not unmapped_output:
            fp.write(u"""N_unmapped	2026581	2026581	2026581
N_multimapping	4020538	4020538	4020538
N_noFeature	8533504	24725707	8782932
N_ambiguous	618069	13658	192220
ENSMUSG00000102592.1	0	0	0
ENSMUSG00000088333.2	0	0	0
ENSMUSG00000103265.1	4	0	4
ENSMUSG00000103922.1	23	23	0
ENSMUSG00000033845.13	437	0	437
ENSMUSG00000102275.1	19	0	19
ENSMUSG00000025903.14	669	2	667
ENSMUSG00000104217.1	0	0	0
ENSMUSG00000033813.15	805	0	805
ENSMUSG00000062588.4	11	11	0
ENSMUSG00000103280.1	9	9	0
ENSMUSG00000002459.17	3	3	0
ENSMUSG00000064363.1	74259	393	73866
ENSMUSG00000064364.1	0	0	0
ENSMUSG00000064365.1	0	0	0
ENSMUSG00000064366.1	0	0	0
ENSMUSG00000064367.1	148640	7892	152477
ENSMUSG00000064368.1	44003	42532	13212
ENSMUSG00000064369.1	6	275	6
ENSMUSG00000064370.1	122199	199	123042
""")
        else:
            fp.write(u"""N_unmapped	1	1	1
N_multimapping	0	0	0
N_noFeature	0	0	0
N_ambiguous	0	0	0
ENSG00000223972.5	0	0	0
ENSG00000227232.5	0	0	0
ENSG00000278267.1	0	0	0
ENSG00000243485.3	0	0	0
ENSG00000274890.1	0	0	0
ENSG00000237613.2	0	0	0
ENSG00000268020.3	0	0	0
ENSG00000240361.1	0	0	0
ENSG00000186092.4	0	0	0
ENSG00000238009.6	0	0	0
""")

class TestStrandTsar(unittest.TestCase):
    def setUp(self):
        # Make a temporary working directory
        self.wd = tempfile.mkdtemp(prefix="TestStrandTsar")
        # Move to the working directory
        self.pwd = os.getcwd()
        os.chdir(self.wd)
        # Store the initial PATH
        self.path = os.environ['PATH']
        # Make a mock STAR executable
        star_bin = os.path.join(self.wd,"mock_star")
        os.mkdir(star_bin)
        mock_star = os.path.join(star_bin,"STAR")
        self._make_mock_star(mock_star)
        # Prepend mock STAR location to the path
        os.environ['PATH'] = "%s:%s" % (star_bin,os.environ['PATH'])
        # Make some mock Fastqs
        self.fqs = []
        for r in ("R1","R2"):
            fq = os.path.join(self.wd,"mock_%s.fq" %r)
            with io.open(fq,'wt') as fp:
                if r == "R1":
                    fp.write(fq_r1_data)
                else:
                    fp.write(fq_r1_data)
            self.fqs.append(fq)
        # Make some mock STAR indices
        for i in ("Genome1","Genome2"):
            os.mkdir(os.path.join(self.wd,i))
        # Make a conf file
        self.conf_file = os.path.join(self.wd,"genomes.conf")
        with io.open(self.conf_file,'wt') as fp:
            for i in ("Genome1","Genome2"):
                fp.write(u"%s\t%s\n" % (i,os.path.join(self.wd,i)))
        # Make a "bad" Fastq
        self.bad_fastq = os.path.join(self.wd,"bad_R1.fq")
        with io.open(self.bad_fastq,'wt') as fp:
            fp.write(u"NOT A FASTQ FILE")
    def tearDown(self):
        # Move back to the original directory
        os.chdir(self.pwd)
        # Reset the PATH
        os.environ['PATH'] = self.path
        # Remove the working dir
        shutil.rmtree(self.wd)
    def _make_mock_star(self,path,unmapped_output=False):
        # Make a mock STAR executable
        with io.open(path,'wt') as fp:
            fp.write(u"""#!/bin/bash
export PYTHONPATH=%s:$PYTHONPATH
python -c "import sys ; from fastq_strand import mockSTAR ; mockSTAR(sys.argv[1:],unmapped_output=%s)" $@
exit $?
""" % (os.path.dirname(__file__),unmapped_output))
        os.chmod(path,0o775)
    def _make_failing_mock_star(self,path):
        # Make a failing mock STAR executable
        with io.open(path,'wt') as fp:
            fp.write(u"""#!/bin/bash
exit 1
""")
        os.chmod(path,0o775)
    def test_fastq_strand_one_genome_index_SE(self):
        """
        fastq_strand: test with single genome index (SE)
        """
        fastq_strand(["-g","Genome1",self.fqs[0]])
        outfile = os.path.join(self.wd,"mock_R1_fastq_strand.txt")
        self.assertTrue(os.path.exists(outfile))
        self.assertEqual(io.open(outfile,'rt').read(),
                         """#fastq_strand version: %s	#Aligner: STAR	#Reads in subset: 3
#Genome	1st forward	2nd reverse
Genome1	13.13	93.21
""" % __version__)
    def test_fastq_strand_two_genome_indices_SE(self):
        """
        fastq_strand: test with two genome indices (SE)
        """
        fastq_strand(["-g","Genome1",
                      "-g","Genome2",
                      self.fqs[0]])
        outfile = os.path.join(self.wd,"mock_R1_fastq_strand.txt")
        self.assertTrue(os.path.exists(outfile))
        self.assertEqual(io.open(outfile,'rt').read(),
                         """#fastq_strand version: %s	#Aligner: STAR	#Reads in subset: 3
#Genome	1st forward	2nd reverse
Genome1	13.13	93.21
Genome2	13.13	93.21
""" % __version__)
    def test_fastq_strand_one_genome_index_PE(self):
        """
        fastq_strand: test with single genome index (PE)
        """
        fastq_strand(["-g","Genome1",
                      self.fqs[0],
                      self.fqs[1]])
        outfile = os.path.join(self.wd,"mock_R1_fastq_strand.txt")
        self.assertTrue(os.path.exists(outfile))
        self.assertEqual(io.open(outfile,'rt').read(),
                         """#fastq_strand version: %s	#Aligner: STAR	#Reads in subset: 3
#Genome	1st forward	2nd reverse
Genome1	13.13	93.21
""" % __version__)
    def test_fastq_strand_two_genome_indices_PE(self):
        """
        fastq_strand: test with two genome indices (PE)
        """
        fastq_strand(["-g","Genome1",
                      "-g","Genome2",
                      self.fqs[0],
                      self.fqs[1]])
        outfile = os.path.join(self.wd,"mock_R1_fastq_strand.txt")
        self.assertTrue(os.path.exists(outfile))
        self.assertEqual(io.open(outfile,'rt').read(),
                         """#fastq_strand version: %s	#Aligner: STAR	#Reads in subset: 3
#Genome	1st forward	2nd reverse
Genome1	13.13	93.21
Genome2	13.13	93.21
""" % __version__)
    def test_fastq_strand_using_conf_file(self):
        """
        fastq_strand: test with genome indices specified via conf file
        """
        fastq_strand(["-c",self.conf_file,
                      self.fqs[0],
                      self.fqs[1]])
        outfile = os.path.join(self.wd,"mock_R1_fastq_strand.txt")
        self.assertTrue(os.path.exists(outfile))
        self.assertEqual(io.open(outfile,'rt').read(),
                         """#fastq_strand version: %s	#Aligner: STAR	#Reads in subset: 3
#Genome	1st forward	2nd reverse
Genome1	13.13	93.21
Genome2	13.13	93.21
""" % __version__)
    def test_fastq_strand_no_subset(self):
        """
        fastq_strand: test with no subset
        """
        fastq_strand(["-g","Genome1",
                      "--subset=0",
                      self.fqs[0],
                      self.fqs[1]])
        outfile = os.path.join(self.wd,"mock_R1_fastq_strand.txt")
        self.assertTrue(os.path.exists(outfile))
        self.assertEqual(io.open(outfile,'rt').read(),
                         """#fastq_strand version: %s	#Aligner: STAR	#Reads in subset: 3
#Genome	1st forward	2nd reverse
Genome1	13.13	93.21
""" % __version__)
    def test_fastq_strand_include_counts(self):
        """
        fastq_strand: test including the counts
        """
        fastq_strand(["-g","Genome1",
                      "--counts",
                      self.fqs[0],
                      self.fqs[1]])
        outfile = os.path.join(self.wd,"mock_R1_fastq_strand.txt")
        self.assertTrue(os.path.exists(outfile))
        self.assertEqual(io.open(outfile,'rt').read(),
                         """#fastq_strand version: %s	#Aligner: STAR	#Reads in subset: 3
#Genome	1st forward	2nd reverse	Unstranded	1st read strand aligned	2nd read strand aligned
Genome1	13.13	93.21	391087	51339	364535
""" % __version__)
    def test_fastq_strand_keep_star_output(self):
        """
        fastq_strand: test keeping the output from STAR
        """
        fastq_strand(["-g","Genome1",
                      "--keep-star-output",
                      self.fqs[0],
                      self.fqs[1]])
        outfile = os.path.join(self.wd,"mock_R1_fastq_strand.txt")
        self.assertTrue(os.path.exists(outfile))
        self.assertEqual(io.open(outfile,'rt').read(),
                         """#fastq_strand version: %s	#Aligner: STAR	#Reads in subset: 3
#Genome	1st forward	2nd reverse
Genome1	13.13	93.21
""" % __version__)
        self.assertTrue(os.path.exists(
            os.path.join(self.wd,
                         "STAR.mock_R1.outputs")))
        self.assertTrue(os.path.exists(
            os.path.join(self.wd,
                         "STAR.mock_R1.outputs",
                         "Genome1")))
        self.assertTrue(os.path.exists(
            os.path.join(self.wd,
                         "STAR.mock_R1.outputs",
                         "Genome1",
                         "fastq_strand_ReadsPerGene.out.tab")))
    def test_fastq_strand_overwrite_existing_output_file(self):
        """
        fastq_strand: test overwrite existing output file
        """
        outfile = os.path.join(self.wd,"mock_R1_fastq_strand.txt")
        with io.open(outfile,'wt') as fp:
            fp.write(u"Pre-existing file should be overwritten")
        fastq_strand(["-g","Genome1",
                      self.fqs[0],
                      self.fqs[1]])
        self.assertTrue(os.path.exists(outfile))
        self.assertEqual(io.open(outfile,'rt').read(),
                         """#fastq_strand version: %s	#Aligner: STAR	#Reads in subset: 3
#Genome	1st forward	2nd reverse
Genome1	13.13	93.21
""" % __version__)
    def test_fastq_strand_handle_STAR_non_zero_exit_code(self):
        """
        fastq_strand: handle STAR exiting with non-zero exit code
        """
        # Make a failing mock STAR executable
        mock_star = os.path.join(self.wd,"mock_star","STAR")
        self._make_failing_mock_star(mock_star)
        outfile = os.path.join(self.wd,"mock_R1_fastq_strand.txt")
        with io.open(outfile,'wt') as fp:
            fp.write(u"Pre-existing file should be removed")
        self.assertRaises(Exception,
                          fastq_strand,
                          ["-g","Genome1",self.fqs[0],self.fqs[1]])
        self.assertFalse(os.path.exists(outfile))
    def test_fastq_strand_no_output_file_on_failure(self):
        """
        fastq_strand: don't produce output file on failure
        """
        # Make a failing mock STAR executable
        mock_star = os.path.join(self.wd,"mock_star","STAR")
        self._make_failing_mock_star(mock_star)
        outfile = os.path.join(self.wd,"mock_R1_fastq_strand.txt")
        with io.open(outfile,'wt') as fp:
            fp.write(u"Pre-existing file should be removed")
        self.assertRaises(Exception,
                          fastq_strand,
                          ["-g","Genome1",self.fqs[0],self.fqs[1]])
        self.assertFalse(os.path.exists(outfile))
    def test_fastq_strand_handle_bad_fastq(self):
        """
        fastq_strand: gracefully handle bad Fastq input
        """
        self.assertRaises(Exception,
                          fastq_strand,
                          ["-g","Genome1",self.bad_fastq,self.fqs[1]])
        outfile = os.path.join(self.wd,"mock_R1_fastq_strand.txt")
        self.assertFalse(os.path.exists(outfile))
    def test_fastq_strand_overwrite_existing_output_file_on_failure(self):
        """
        fastq_strand: test overwrite existing output file on failure
        """
        # Make a failing mock STAR executable
        mock_star = os.path.join(self.wd,"mock_star","STAR")
        self._make_failing_mock_star(mock_star)
        outfile = os.path.join(self.wd,"mock_R1_fastq_strand.txt")
        with io.open(outfile,'wt') as fp:
            fp.write(u"Pre-existing file should be overwritten")
        self.assertRaises(Exception,
                          fastq_strand,
                          ["-g","Genome1",self.fqs[0],self.fqs[1]])
        self.assertFalse(os.path.exists(outfile))
    def test_fastq_strand_single_unmapped_read_PE(self):
        """
        fastq_strand: test single unmapped read from STAR (PE)
        """
        # Make a mock STAR executable which produces unmapped
        # output
        mock_star = os.path.join(self.wd,"mock_star","STAR")
        self._make_mock_star(mock_star,unmapped_output=True)
        fastq_strand(["-g","Genome1",
                      self.fqs[0],
                      self.fqs[1]])
        outfile = os.path.join(self.wd,"mock_R1_fastq_strand.txt")
        self.assertTrue(os.path.exists(outfile))
        self.assertEqual(io.open(outfile,'rt').read(),
                         """#fastq_strand version: %s	#Aligner: STAR	#Reads in subset: 3
#Genome	1st forward	2nd reverse
Genome1	0.00	0.00
""" % __version__)

#######################################################################
# Main script
#######################################################################

def fastq_strand(argv,working_dir=None):
    """
    Driver for fastq_strand

    Generate strandedness statistics for single FASTQ or
    FASTQ pair, by running STAR using one or more genome
    indexes
    """
    # Process command line
    p = argparse.ArgumentParser(
        description="Generate strandedness statistics "
        "for FASTQ or FASTQpair, by running STAR using "
        "one or more genome indexes")
    p.add_argument('--version',action='version',version=__version__)
    p.add_argument("r1",metavar="READ1",
                   default=None,
                   help="R1 Fastq file")
    p.add_argument("r2",metavar="READ2",
                   default=None,
                   nargs="?",
                   help="R2 Fastq file")
    p.add_argument("-g","--genome",
                   dest="star_genomedirs",metavar="GENOMEDIR",
                   default=None,
                   action="append",
                   help="path to directory with STAR index "
                   "for genome to use (use as an alternative "
                   "to -c/--conf; can be specified multiple "
                   "times to include additional genomes)")
    p.add_argument("--subset",
                   type=int,
                   default=10000,
                   help="use a random subset of read pairs "
                   "from the input Fastqs; set to zero to "
                   "use all reads (default: 10000)")
    p.add_argument("-o","--outdir",
                   default=None,
                   help="specify directory to write final "
                   "outputs to (default: current directory)")
    p.add_argument("-c","--conf",metavar="FILE",
                   default=None,
                   help="specify delimited 'conf' file with "
                   "list of NAME and STAR index directory "
                   "pairs. NB if a conf file is supplied "
                   "then any indices specifed on the command "
                   "line will be ignored")
    p.add_argument("-n",
                   type=int,
                   default=1,
                   help="number of threads to run STAR with "
                   "(default: 1)")
    p.add_argument("--counts",
                   action="store_true",
                   help="include the count sums for "
                   "unstranded, 1st read strand aligned and "
                   "2nd read strand aligned in the output "
                   "file (default: only include percentages)")
    p.add_argument("--keep-star-output",
                   action="store_true",
                   help="keep the output from STAR (default: "
                   "delete outputs on completion)")
    args = p.parse_args(argv)
    # Print parameters
    print("READ1\t: %s" % args.r1)
    print("READ2\t: %s" % args.r2)
    # Check that STAR is on the path
    star_exe = find_program("STAR")
    if star_exe is None:
        logging.critical("STAR not found")
        return 1
    print("STAR\t: %s" % star_exe)
    # Gather genome indices
    genome_names = {}
    if args.conf is not None:
        print("Conf file\t: %s" % args.conf)
        star_genomedirs = []
        with io.open(args.conf,'rt') as fp:
            for line in fp:
                if line.startswith('#'):
                    continue
                name,star_genomedir = line.rstrip().split('\t')
                star_genomedirs.append(star_genomedir)
                # Store an associated name
                genome_names[star_genomedir] = name
    else:
        star_genomedirs = args.star_genomedirs
    if not star_genomedirs:
        logging.critical("No genome indices specified")
        return 1
    print("Genomes:")
    for genome in star_genomedirs:
        print("- %s" % genome)
    # Output directory
    if args.outdir is None:
        outdir = os.getcwd()
    else:
        outdir = os.path.abspath(args.outdir)
    if not os.path.exists(outdir):
        logging.critical("Output directory doesn't exist: %s" %
                         outdir)
        return 1
    # Output file
    outfile = "%s_fastq_strand.txt" % os.path.join(
        outdir,
        os.path.basename(strip_ngs_extensions(args.r1)))
    if os.path.exists(outfile):
        logging.warning("Removing existing output file '%s'" % outfile)
        os.remove(outfile)
    # Prefix for temporary output
    prefix = "fastq_strand_"
    # Working directory
    if working_dir is None:
        working_dir = os.getcwd()
    else:
        working_dir = os.path.abspath(working_dir)
        if not os.path.isdir(working_dir):
            raise Exception("Bad working directory: %s" % working_dir)
    print("Working directory: %s" % working_dir)
    # Make subset of input read pairs
    nreads = sum(1 for i in getreads(os.path.abspath(args.r1)))
    print("%d reads" % nreads)
    if args.subset == 0:
        print("Using all read pairs in Fastq files")
        subset = nreads
    elif args.subset > nreads:
        print("Actual number of read pairs smaller than requested subset")
        subset = nreads
    else:
        subset = args.subset
        print("Using random subset of %d read pairs" % subset)
    if subset == nreads:
        subset_indices = [i for i in range(nreads)]
    else:
        subset_indices = random.sample(range(nreads),subset)
    fqs_in = filter(lambda fq: fq is not None,(args.r1,args.r2))
    fastqs = []
    for fq in fqs_in:
        fq_subset = os.path.join(working_dir,
                                 os.path.basename(fq))
        if fq_subset.endswith(".gz"):
            fq_subset = '.'.join(fq_subset.split('.')[:-1])
        fq_subset = "%s.subset.fq" % '.'.join(fq_subset.split('.')[:-1])
        with io.open(fq_subset,'wt') as fp:
            for read in getreads_subset(os.path.abspath(fq),
                                        subset_indices):
                fp.write(u'\n'.join(read) + '\n')
        fastqs.append(fq_subset)
    # Make directory to keep output from STAR
    if args.keep_star_output:
        star_output_dir = os.path.join(outdir,
                                       "STAR.%s.outputs" %
                                       os.path.basename(
                                           strip_ngs_extensions(args.r1)))
        print("Output from STAR will be copied to %s" % star_output_dir)
        # Check if directory already exists from earlier run
        if os.path.exists(star_output_dir):
            # Move out of the way
            i = 0
            backup_dir = "%s.bak" % star_output_dir
            while os.path.exists(backup_dir):
                i += 1
                backup_dir = "%s.bak%s" % (star_output_dir,i)
            logging.warning("Moving existing output directory to %s" %
                            backup_dir)
            os.rename(star_output_dir,backup_dir)
        # Make the directory
        os.mkdir(star_output_dir)
    # Write output to a temporary file
    with tempfile.TemporaryFile(mode='w+t') as fp:
        # Iterate over genome indices
        for star_genomedir in star_genomedirs:
            # Basename for output for this genome
            try:
                name = genome_names[star_genomedir]
            except KeyError:
                name = star_genomedir
            # Build a command line to run STAR
            star_cmd = [star_exe]
            star_cmd.extend([
                '--runMode','alignReads',
                '--genomeLoad','NoSharedMemory',
                '--genomeDir',os.path.abspath(star_genomedir)])
            star_cmd.extend(['--readFilesIn',
                             fastqs[0]])
            if len(fastqs) > 1:
                star_cmd.append(fastqs[1])
            star_cmd.extend([
                '--quantMode','GeneCounts',
                '--outSAMtype','BAM','Unsorted',
                '--outSAMstrandField','intronMotif',
                '--outFileNamePrefix',prefix,
                '--runThreadN',str(args.n)])
            print("Running %s" % ' '.join(star_cmd))
            try:
                subprocess.check_output(star_cmd,cwd=working_dir)
            except subprocess.CalledProcessError as ex:
                raise Exception("STAR returned non-zero exit code: %s" %
                                ex.returncode)
            # Save the outputs
            if args.keep_star_output:
                # Make a subdirectory for this genome index
                genome_dir = os.path.join(star_output_dir,
                                          name.replace(os.sep,"_"))
                print("Copying STAR outputs to %s" % genome_dir)
                os.mkdir(genome_dir)
                for f in os.listdir(working_dir):
                    if f.startswith(prefix):
                        shutil.copy(os.path.join(working_dir,f),
                                    os.path.join(genome_dir,f))
            # Process the STAR output
            star_tab_file = os.path.join(working_dir,
                                         "%sReadsPerGene.out.tab" % prefix)
            if not os.path.exists(star_tab_file):
                raise Exception("Failed to find .out file: %s" % star_tab_file)
            sum_col2 = 0
            sum_col3 = 0
            sum_col4 = 0
            with io.open(star_tab_file,'rt') as out:
                for i,line in enumerate(out):
                    if i < 4:
                        # Skip first four lines
                        continue
                    # Process remaining delimited columns
                    cols = line.rstrip('\n').split('\t')
                    sum_col2 += int(cols[1])
                    sum_col3 += int(cols[2])
                    sum_col4 += int(cols[3])
            print("Sums:")
            print("- col2: %d" % sum_col2)
            print("- col3: %d" % sum_col3)
            print("- col4: %d" % sum_col4)
            if sum_col2 > 0.0:
                forward_1st = float(sum_col3)/float(sum_col2)*100.0
                reverse_2nd = float(sum_col4)/float(sum_col2)*100.0
            else:
                logging.warning("Sum of mapped reads is zero!")
                forward_1st = 0.0
                reverse_2nd = 0.0
            print("Strand percentages:")
            print("- 1st forward: %.2f%%" % forward_1st)
            print("- 2nd reverse: %.2f%%" % reverse_2nd)
            # Append to output file
            data = [name,
                    "%.2f" % forward_1st,
                    "%.2f" % reverse_2nd]
            if args.counts:
                data.extend([sum_col2,sum_col3,sum_col4])
            fp.write(u"%s\n" % "\t".join([str(d) for d in data]))
        # Finished iterating over genomes
        # Rewind temporary output file
        fp.seek(0)
        with io.open(outfile,'wt') as out:
            # Header
            out.write(u"#fastq_strand version: %s\t"
                      "#Aligner: %s\t"
                      "#Reads in subset: %s\n" % (__version__,
                                                  "STAR",
                                                  subset))
            columns = ["Genome","1st forward","2nd reverse"]
            if args.counts:
                columns.extend(["Unstranded",
                                "1st read strand aligned",
                                "2nd read strand aligned"])
            out.write(u"#%s\n" % "\t".join(columns))
            # Copy content from temp to final file
            for line in fp:
                out.write(str(line))
    return 0

if __name__ == "__main__":
    # Start up
    print("Fastq_strand: version %s" % __version__)
    # Create a temporary working directory
    working_dir = tempfile.mkdtemp(suffix=".fastq_strand",
                                   dir=os.getcwd())
    try:
        retval = fastq_strand(sys.argv[1:],
                              working_dir=working_dir)
    except Exception as ex:
        logging.critical("Exception: %s" % ex)
        retval = 1
    # Clean up the working dir
    print("Cleaning up working directory")
    shutil.rmtree(working_dir)
    print("Fast_strand: finished")
    sys.exit(retval)

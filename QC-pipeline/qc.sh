#!/bin/sh
#
# Script to run QC steps on SOLiD data
#
# Usage: qc.sh <csfasta> <qual>
#
function usage() {
    echo "Usage: qc.sh <csfasta_file> <qual_file>"
    echo ""
    echo "Run QC pipeline:"
    echo ""
    echo "* create fastq file"
    echo "* check for contamination using fastq_screen"
    echo "* generate QC boxplots"
    echo "* preprocess/filter using polyclonal and error tests"
    echo "  and generate fastq and boxplots for filtered data"
}
#
# QC pipeline consists of the following steps:
#
# Primary data:
# * create fastq files (solid2fastq)
# * check for contamination (fastq_screen)
# * generate QC boxplots (qc_boxplotter)
# * filter primary data and make new csfastq/qual files
#   (SOLiD_preprocess_filter)
# * remove unwanted filter files
# * generate QC boxplots for filtered data (qc_boxplotter)
# * compare number of reads after filtering with original
#   data files
#
# Check command line
if [ $# -ne 2 ] || [ "$1" == "-h" ] || [ "$1" == "--help" ] ; then
    usage
    exit
fi
#
#===========================================================================
# Import function libraries
#===========================================================================
#
# General shell functions
if [ -f functions.sh ] ; then
    # Import local copy
    . functions.sh
else
    # Import version in share
    . `dirname $0`/../share/functions.sh
fi
#
# NGS-specific functions
if [ -f ngs_utils.sh ] ; then
    # Import local copy
    . ngs_utils.sh
else
    # Import version in share
    . `dirname $0`/../share/ngs_utils.sh
fi
#
#===========================================================================
# Main script
#===========================================================================
#
# Set umask to allow group read-write on all new files etc
umask 0002
#
# Get the input files
CSFASTA=$(abs_path $1)
QUAL=$(abs_path $2)
#
#
if [ ! -f "$CSFASTA" ] || [ ! -f "$QUAL" ] ; then
    echo "csfasta and/or qual files not found"
    exit
fi
#
# Get the data directory i.e. location of the input files
datadir=`dirname $CSFASTA`
#
# Report
echo ========================================================
echo QC pipeline
echo ========================================================
echo Started   : `date`
echo Running in: `pwd`
echo data dir  : $datadir
echo csfasta   : `basename $CSFASTA`
echo qual      : `basename $QUAL`
#
# Set up environment
QC_SETUP=`dirname $0`/qc.setup
if [ -f "${QC_SETUP}" ] ; then
    echo Sourcing qc.setup to set up environment
    . ${QC_SETUP}
else
    echo WARNING qc.setup not found in `dirname $0`
fi
#
# Working directory
WORKING_DIR=`pwd`
#
# Set the programs
# Override these defaults by setting them in qc.setup
: ${FASTQ_SCREEN:=fastq_screen}
: ${FASTQ_SCREEN_CONF_DIR:=}
: ${SOLID2FASTQ:=solid2fastq}
: ${QC_BOXPLOTTER:=qc_boxplotter.sh}
: ${SOLID_PREPROCESS_FILTER:=SOLiD_preprocess_filter_v2.pl}
#
# Check: both files should exist
if [ ! -f "$CSFASTA" ] || [ ! -f "$QUAL" ] ; then
    echo ERROR one or both of csfasta or qual files not found
    exit 1
fi
# Check: both files should be in the same directory
if [ `dirname $CSFASTA` != `dirname $QUAL` ] ; then
    echo ERROR csfasta and qual are in different directories
    exit 1
fi
#
# Run solid2fastq to make fastq file
run_solid2fastq ${CSFASTA} ${QUAL}
#
# Create 'qc' subdirectory
if [ ! -d "qc" ] ; then
    mkdir qc
fi
#
# Run fastq_screen
fastq=$(baserootname $CSFASTA).fastq
run_fastq_screen --color $fastq
#
# SOLiD_preprocess_filter
solid_preprocess_filter ${CSFASTA} ${QUAL}
#
# QC_boxplots
#
# Move to qc directory
cd qc
#
# Boxplots for original primary data
qc_boxplotter $QUAL
#
# Boxplots for filtered data
qual=`echo $(solid_preprocess_files ${WORKING_DIR}/$(baserootname $CSFASTA)) | cut -d" " -f2`
if [ ! -z "$qual" ] ; then
    qc_boxplotter $qual
else
    echo Unable to locate preprocess filtered QUAL file, boxplot skipped
fi
#
echo QC pipeline completed: `date`
exit
#

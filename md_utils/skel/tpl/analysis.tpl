#!/bin/bash
#PBS -N resubmit
#PBS -l walltime=5:00
#PBS -l nodes=1:ppn=1,pmem=1g
#PBS -A hbmayes_fluxod
#PBS -q fluxod
#PBS -V
#PBS -j oe
#PBS -m e
set -u
set -e
cd ~
# This submits this job file again, but makes sure
# that it waits in the queue for at least 10 minutes
files=
basename=

for file in ${{files[@]}}
do
    namd_scripts -p -f ${file}.log
done
python -c "from md_utils import scaling; scaling.plot_scaling('$files','$basename')"

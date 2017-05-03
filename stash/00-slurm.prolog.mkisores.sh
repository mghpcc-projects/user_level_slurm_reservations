#!/bin/bash
#
# This script will create an isolation reservation for a 
# SLURM job if the job partition name matches a certain 
# pattern.
#
# SLURM_BIN can be used for testing with private version of SLURM
#SLURM_BIN="/usr/bin/"
logdir="/home/cnh/tmp"
#
function check_within_slurm(){
if [ x$SLURM_UID == "x" ] ; then
        exit 0
fi
if [ x$SLURM_JOB_ID == "x" ] ; then
        exit 0
fi
}

function set_log_file(){
 hn=`hostname`
 mkdir -p ${logdir}/${hn}
}

# check_within_slurm

# set_log_file

job_list=$( squeue --noheader --format=%A --node=localhost )
if [ x${job_list} = "x" ]; then
 exit 0
fi

#
# Check that this is a single exclusive job
# =========================================
nj=0
for j in ${job_list} ; do
 nj=$((${nj}+1))
done
if [ "${nj}" -ne "1" ]; then
 exit 0
fi

# Get partition for the job and check name is "flexalloc.*" and it is configured as EXCLUSIVE
jp=`sacct -j ${job_list} -n -P -o partition`

if [[ "${jp}" != flexalloc_* ]]; then
 exit 0
fi

# Check it has OverSubscribe=EXCLUSIVE
exv=`scontrol -o show partition=${jp} | sed s'/.*OverSubscribe=\([^ ]*\) .*/\1/'`
if [ "x${exv}" != "xEXCLUSIVE" ]; then
 exit 0
fi

#
# Exclusive job so create reservation command for these nodes, ending at the job end time
#
nodelist=`sacct -P -o NodeList -n -j ${job_list}`
stime=`sacct -P -o Start -n -j ${job_list}`
ltime=`sacct -P -o TimeLimit -n -j ${job_list}`
uname=`sacct -P -o User -n -j ${job_list}`
rsuff=`date +"%Y%m%d_%H_%m_%S_${job_list}"`

hn=`hostname`
n0=(`scontrol show hostname ${nodelist}`)
if [ ${hn} = ${n0[0]} ]; then
 scontrol create reservation=${jp}_${rsuff} starttime=now duration=${ltime} flags=maint,ignore_jobs users=root,${uname} nodes=${nodelist}
 scontrol create reservation=${jp}_${rsuff}_cleanup starttime=now duration=infinite flags=maint,ignore_jobs users=root nodes=${nodelist}
fi
set >> /home/cnh/tmp/foo
env >> /home/cnh/tmp/foo
id  >> /home/cnh/tmp/foo

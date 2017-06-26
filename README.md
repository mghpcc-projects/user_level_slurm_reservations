# MOC HIL Node Reservations

(Also known as 'user_level_slurm_reservations')

V0.1 26-Jun-2017

# Introduction

HIL reservations allow a nonprivileged Slurm user to reserve Slurm
compute nodes for HIL operations.  The nodes may be later released
and returned to the pool of Slurm compute nodes for use by others.

At present, two commands are used to manage HIL reservations:

  * ```hil_reserve```
  * ```hil_release```

These commands are executed as Slurm jobs via ```srun(1)``` and ```sbatch(1).```

In future, additional commands may be made available to conduct
low-level HIL node operations.  For example:

  * hil_init - Initialize HIL nodes and networking infrastructure to a
  desired state
  * hil_restore - Restore a HIL node to a Slurm partition, with it
  again behaving as a Slurm compute node 


## Usage

To reserve a HIL node, specify the ```hil_reserve``` command as a job
to the Slurm ```srun(1)``` or ```sbatch(1)``` command:

```
$ srun hil_reserve
```

To verify the reservation was created, run the ```scontrol show
reservation``` command:

``` 
$ scontrol show reservation
```
If successful, a reservation similiar to the following should appear:

```
ReservationName=flexalloc_MOC_ubuntu_1000_2017-06-26T17:20:32
StartTime=2017-06-26T17:20:32 EndTime=2017-06-26T21:25:32
Duration=04:05:00 Nodes=server1 NodeCnt=1 CoreCnt=1 Features=(null)
PartitionName=(null) Flags=MAINT,IGNORE_JOBS,S PEC_NODES,ALL_NODES
TRES=cpu=1 Users=ubuntu Accounts=(null) Licenses=(null) State=ACTIVE
BurstBuffer=(null) Watts=n/a 
```

When finished, to release a HIL node, specify the ```hil_release```
command to ```srun(1)``` or ```sbatch(1)```, additionally specifying
**the HIL reservation to be released** as the reservation in which to
run the job:

```
$ srun --reservation=flexalloc_MOC_ubuntu_1000_2017-06-26T17:20:32 hil_release
```

## Reservation Naming

HIL reservations created using ```hil_reserve``` are named as follows:
```
flexalloc_MOC_<username>_<uid>_<start_time>
```
An example:
```
flexalloc_MOC_ubuntu_1000_2017-06-26T17:20:32
```

The ```start_time``` is the start time of the job.


# Assumptions, Restrictions, Notes

  1. All nodes in the HIL reservation pool are configured in a single
  Slurm partition.  

  2. The Slurm controller node in the partition is not available for
  HIL operations.

  3. Slurm compute nodes must be marked with the HIL feature in order
  to be reserved.  Features are defined in the slurm.conf file or may
  be added to a node by a privileged user via the ```scontrol
  update``` command.

  4. HIL nodes may be released from a HIL reservation through the use
  of ```hil_release``` even though they are not up and running.

  5. Python version 2.7 is installed on the Slurm controller node.


# Logging

Slurm and the HIL reservation system maintain several log files which
may be reviewed as necessary to gain insight into system behavior.

  * The Slurm control daemon (```slurmctld```) running on the Slurm
  controller node writes to a log file, the location of which is
  defined by the ```SlurmctldLogFile``` parameter in the
  ```slurm.conf``` file.

  * HIL reservation operations are logged to a file on the Slurm
    controller node.  The location of this file is configured in the
    ```hil_slurm_settings.py``` file.

By default, the following paths are used:
```/var/log/slurm-llnl/slurmctld.log```
```/var/log/slurm-llnl/hil_prolog.log```


# Implementation Details

## Slurm Control Daemon Prolog and Epilog

## HIL Reservation Commands

##


# Software Installation 

## HIL Software Installation

## Support Libraries

### python-hostlist

Install python-hostlist on the Slurm controller node:
```
$ cd /usr/local/lib/python2.7/site-packages
$ wget https://www.nsc.liu.se/~kent/python-hostlist/python-hostlist-1.17.tar.gz
$ tar xvf python-hostlist-1.17.tar.gz
$ cd python-hostlist-1.17
$ python setup.py build
$ python setup.py install
```

## User .hil Subdirectory

# Software Configuration

## SlurmCtld Prolog and Epilog

The SlurmCtld prolog and epilog must be specified:

PrologSlurmctld=/<install_dir>/prolog/hil_slurmctld_prolog.sh
EpilogSlurmctld=/<install_dir>/prolog/hil_slurmctld_epilog.sh

### MaxTime and DefaultTime

The partition MaxTime and DefaultTime must be set so that to values
other than 'INFINITE' or 'UNLIMITED', so that the hil_reserve and (in
particular) hil_release commands are not queued and blocked when other
reservations, starting at future times, exist in the partition and
include the

The illustrated times are arbitrary.

PartitionName=debug Nodes=server[1] Default=YES DefaultTime=00:05:00 MaxTime=06:00:00 State=UP Shared=No


<EOF>



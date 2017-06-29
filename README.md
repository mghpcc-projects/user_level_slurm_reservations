# MOC HIL Node Reservations

(Also known as 'user_level_slurm_reservations')

V0.2  27-Jun-2017

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
  to be reserved.  Features are defined in the ```slurm.conf``` file
  or may be added to a node by a privileged user via the ```scontrol
  update``` command.

  4. HIL nodes may be released from a HIL reservation through
  ```hil_release```, even though they are not up and running Linux.
  Some error messages may appear in the Slurmctld log file.

  5. Python version 2.7 must be installed on the Slurm controller node.


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
```/var/log/slurm-llnl/slurmctld.log``` and 
```/var/log/slurm-llnl/hil_prolog.log```


# Implementation Details

## HIL Reservation Commands

The ```hil_reserve``` and ```hil_release``` commands are implemented
as bash(1) shell scripts, which do little more than cause the
```slurmctld`` prolog and epilog to run and recognize that the user
wishes to reserve or release HIL nodes.

## Slurm Control Daemon Prolog and Epilog

The ```slurmctld``` prolog performs does the work required to place
nodes in a HIL reservation.  The prolog consists of a ```bash```
script which invokes a common Python program used for both the prolog
and the epilog.  Prolog function is selected via an argument to the
Python script.  The epilog is implemented in an identical manner.

The work required to release nodes from a HIL reservation is performed
by the ```slurmctld``` epilog.  As the reservation to be released is
in use at the time the prolog runs (it will be used to run the
```hil_release``` job), it is not possible to delete the reservation
in the prolog.

## Communication between Components

The ```slurmctld``` prolog and epilog execution environment provides
very limited support for communication between the user, the user's
job, and the prolog and epilog, apart from Linux file system I/O.  For
example, it is not possible for the prolog or epilog to write status
information to the user's TTY, nor is is possible for the user's job
to pass arguments to the prolog or epilog.  Note: It may be possible
to output information to the user through a SPANK plugin, but that
possibility is not considered further here.

The name of the job submitted via ```srun``` or ```sbatch``` is
available to the prolog and epilog through a very limited set of
environment variables.  Also available in the environment are the user
name, user ID, and job node list.  Other information regarding the
Slurm execution environment is available through subprocess execution
of various ```scontrol show``` commands, for example, ```scontrol show job```.


# Software Installation

## HIL Software Installation

TEMPORARY

(The following assumes Slurm-LLNL version 15 or greater is installed
and running.  The installation is targeted on the Slurm controller node)

On the Slurm controller node, create a virtual environment:
```
$ mkdir <HIL_INSTALL_DIR>
$ cd <HIL_INSTALL_DIR>
$ virtualenv ve
$ source ve/bin/activate
```
Fetch the software from GitHub:
``` 
$ git clone git@github.com:mghpcc-projects/user_level_slurm_reservations.git
$ cd user_level_slurm_reservations
```

_CAVEAT_: This must be repeated on all nodes in the Slurm partition, or
filesystem sharing must be used/


## Support Libraries

### python-hostlist

Install the ```python-hostlist``` package on the Slurm controller node:
```
$ cd /usr/local/lib/python2.7/site-packages
$ wget https://www.nsc.liu.se/~kent/python-hostlist/python-hostlist-1.17.tar.gz
$ tar xvf python-hostlist-1.17.tar.gz
$ cd python-hostlist-1.17
$ python setup.py build
$ python setup.py install
```


# Slurm Software Configuration

Slurm software configuration is performed via the ```slurm.conf```
file.  Once changes to this file have been made, copies must be pushed
to all nodes in the Slurm cluster.  In order for changes to take
effect, the ```slurmctld``` must be restarted on the controller, and
the ```slurmd``` must be restarted on the compute nodes.

By default, the ```slurm.conf``` file resides in ```/etc/slurm-llnl/slurm.conf.```

## SlurmCtld Prolog and Epilog Installation

[NEEDS UPDATE to reflect coexistence with other Slurm prolog / epilog modules]

The SlurmCtld prolog and epilog must be specified:

```
PrologSlurmctld=/<install_dir>/prolog/hil_slurmctld_prolog.sh
EpilogSlurmctld=/<install_dir>/prolog/hil_slurmctld_epilog.sh
```

## Compute Nodes Marked with HIL Feature

[NOT YET IMPLEMENTED IN THE CODE]

Slurm compute nodes which are intended to be placed in a HIL
reservation must be marked in the Slurm cluster configuration as
having the Slurm feature 'HIL'.

## Partition MaxTime and DefaultTime

The partition MaxTime and DefaultTime must be set so that to values
other than 'INFINITE' or 'UNLIMITED'.  Otherwise, the
```hil_reserve``` and ```hil_release``` commands may be queued and
blocked when other reservations, starting at future times, exist in
the partition and include the Slurm compute nodes intended for use by
HIL.

In the following example, the illustrated times are arbitrary.

```
PartitionName=debug Nodes=server[1] Default=YES DefaultTime=00:05:00 MaxTime=06:00:00 State=UP Shared=No
```

## Default Nodes

Might not want a HIL node to be among the partition default nodes.

## Node Sharing and Oversubscription

Must be disabled.

<EOF>



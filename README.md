# MOC HIL User Level Slurm Reservations (ULSR)

V3.0  16-Nov-2017

# Introduction

ULSR software allows a non-privileged Slurm user to reserve Slurm
compute nodes for HIL operations.  The nodes may be later released and
returned to the pool of Slurm compute nodes for use by others.

At present, two commands, run in the Slurm partition environment, are
used to manage Slurm HIL reservations:

  * ```hil_reserve```
  * ```hil_release```

These commands are executed as Slurm jobs via ```srun(1)``` and
```sbatch(1).```

Other software components perform HIL node and network management
operations on nodes reserved and freed using the above commands.  An
important program goal is to have these components execute
automatically without user or administrator intervention.

## Supported Targets

ULSR is supported on CentOS 7 on x86_64 systems, using Python 2.7.  It may work on Red Hat Enterprise
Linux but has not been tested in that distribution environment.

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
If successful, immediately after execution of the ```srun
hil_reserve``` command, a Slurm reservation similiar to the following
should appear:
```
ReservationName=flexalloc_MOC_reserve_centos_1000_2017-06-26T17:20:32
StartTime=2017-06-26T17:20:32 EndTime=2017-06-26T21:25:32
Duration=04:05:00 Nodes=server1 NodeCnt=1 CoreCnt=1 Features=(null)
PartitionName=(null) Flags=MAINT,IGNORE_JOBS,S PEC_NODES,ALL_NODES
TRES=cpu=1 Users=centos Accounts=(null) Licenses=(null) State=ACTIVE
BurstBuffer=(null) Watts=n/a 
```
This is called the ULSR reserve reservation.

Some time later, after the periodic execution of the ULSR monitor, a
paired release reservation similiar to the following should appear:

```
ReservationName=flexalloc_MOC_release_centos_1000_2017-06-26T17:20:32
StartTime=2017-06-26T17:20:32 EndTime=2017-06-26T21:25:32
Duration=04:05:00 Nodes=server1 NodeCnt=1 CoreCnt=1 Features=(null)
PartitionName=(null) Flags=MAINT,IGNORE_JOBS,S PEC_NODES,ALL_NODES
TRES=cpu=1 Users=centos Accounts=(null) Licenses=(null) State=ACTIVE
BurstBuffer=(null) Watts=n/a 
```

Note that Slurm allows these reservations to temporally overlap due to
the use of the ```MAINT``` flag during reservation creation.

When finished, to release a HIL node, specify the ```hil_release```
command to ```srun(1)``` or ```sbatch(1)```, additionally specifying
**the HIL reserve reservation name** as the reservation in which to
run the job:

```
$ srun --reservation=flexalloc_MOC_reserve_centos_1000_2017-06-26T17:20:32 hil_release
```
This will ultimately remove both the reserve and release reservations.

## Resource Sharing

Nodes placed in a Slurm HIL reservation are marked as exclusive and
may not be shared among users.

## Reservation Naming

HIL reservations created using ```hil_reserve``` are named as follows:
```
flexalloc_MOC_reserve_<username>_<uid>_<start_time>
```
and
```
flexalloc_MOC_release_<username>_<uid>_<start_time>
```

An example:
```
flexalloc_MOC_reserve_centos_1000_2017-06-26T17:20:32
```

## Restrictions on User Names and UIDs

Reservations are named after the who invoked the user who invoked the
```srun hil_reserve``` command.  The user's name and UID are passed to
the Slurmctld prolog and epilog through the ```SLURM_JOB_USER``` and
```SLURM_JOB_UID``` environment variables.

Priviliged users may specify the user ID with which to create Slurm
reservations by specifying the ```--uid=<name>``` argument.  It is
recommended that the ```srun``` and ```sbatch``` commands **not** be
specified with the ```--uid``` argument, however, as processing Slurm
HIL reservations with alternate or additional user names has not been
tested.

At present, only the user named in the reservation may release the
reservation via ```hil_release```.  Of course, a privileged user may
update or delete reservations using ```scontrol```, but the system
state after such an operation will be **undefined**.

## Reservation Start and End Times

The reserve and release reservation start times may differ from the
time at which the ```hil_reserve``` command is run.  Reservations are
created by the ```slurmctld``` prolog and epilog and the ULSR periodic
monitor only when the requested resources become available and the job
is scheduled for execution.  Thus the reservation start times may be
substantially different from the time-of-day at which the ```srun```
command is invoked.


## Two-Screen Management Model

All HIL nodes are known, by common names, to the Slurm management
functions and to the HIL management functions.  The nodes exist in
both the Slurm partition and the HIL partition simultaneously, in
advance of any reservation and release operations.

In the Slurm partition, nodes marked with the HIL property and perhaps
otherwise designated by system administration may be thought of as
either available for loan to HIL, or actually on loan to a HIL and
either available for use in a HIL end user project, or in use in a HIL
end user project:

  * Nodes which have been placed in a Slurm HIL reservation may be
    considered as on loan to HIL.  They may exist in the HIL free pool
    or be allocated to a HIL project and a HIL end user.

  * Nodes which are not in a Slurm HIL reservation, but which are
    marked with the ```HIL``` property, may be considered as available
    for loan to HIL instance. They do not reside in the HIL free pool, 
    but reside in a special HIL project.  This project is referred to
    as the 'Slurm project' or the 'Slurm loaner project'.

Once a Slurm server node has been placed in a Slurm HIL reservation
through the use of ```hil_reserve```, it may be necessary for the HIL
end user to run HIL management commands to cause the server node to
fully participate in a HIL user project.  This requirement may be
interpreted as consistent with a 'two-screen' management model.


# Assumptions, Restrictions, Notes

Beyond any requirements imposed by the HIL software and Slurm, the
following apply to the user level Slurm reservation software.

  1. All nodes in the HIL reservation pool are configured in a single
  Slurm partition.

  2. Slurm compute nodes must be marked with the ```HIL``` feature in
  order to be placed in a HIL reservation.  Features are defined in
  the ```slurm.conf``` file or may be added to a node by a privileged
  user via the ```scontrol update``` command.  Refer to the Slurm
  documentation for a description of how to do this.

  3. The Slurm controller node in the partition is not available for
  HIL operations and is **not** marked with the ```HIL``` feature.

  4. HIL nodes may be released from a HIL reservation through
  ```hil_release```, even though they are not up and running Linux.
  Some error messages may appear in the Slurmctld log file.  Note that
  detailed system behavior has not been fully evaluated and is likely
  to evolve over time.

  5. Python 2.7 must be installed on the Slurm controller node.

  6. The ```hil_reserve``` and ```hil_release``` commands must be
  available on both the Slurm controller node and on the compute nodes
  which form the target of the HIL bare node operations.  This is
  accomplished during the ULSR software installation process.


# Logging

Slurm and the HIL reservation system maintain several log files which
may be reviewed as necessary to gain insight into system behavior.

  * The Slurm control daemon (```slurmctld```) running on the Slurm
  controller node writes to a log file, the location of which is
  defined by the ```SlurmctldLogFile``` parameter in the
  ```slurm.conf``` file.

  * HIL reservation operations performed by the Slurmctld prolog and
    epilog are logged to a file on the Slurm controller node.  The
    location of this file is configured in the
    ```hil_slurm_settings.py``` file.  By default, the location is
    ```/var/log/moc_hil_ulsr/hil_prolog.log```.

  * HIL reservation operations performed by the HIL periodic monitor
  are also logged to a file on the Slurm controller node.  The
  location of this file is configured in the
  ```hil_slurm_settings.py``` file.  By default, the location is
  ```/var/log/moc_hil_ulsr/hil_monitor.log```. 

  * The HIL server writes to ```/var/log/hil.log```.  Note the HIL
    server may or may not reside on Slurm controller node.


# Implementation Details

## Software Components and Structure

The ULSR software running in the context of the Slurm partition
consists of the following:

  1. The ```hil_reserve``` and ```hil_release``` user commands
  described above.

  2. A dedicated Slurm control daemon prolog function, which runs in
  the context of the Slurm control daemon on the Slurm controller
  node.

  3. One or more periodic processors, scheduled by ```cron(8)```,
  which monitor the set of Slurm reservations and invoke HIL control
  operations to move nodes between HIL projects and the HIL free pool.

  4. A MOC HIL client interface, used by the ULSR code to remotely
  execute HIL commands on the nodes placed into and freed from HIL
  reservations, and on the switches terminating the physical network
  links which interconnect the nodes.

  5. A Slurm partition instance.

  6. A MOC HIL cluster instance.


## Workflow and Functional Partitioning

The general workflow is as follows:

To reserve nodes, as a Slurm non-privilged user run the following command:
```
$ srun hil_reserve
```
ULSR software actions:

  * Slurm Control Daemon ULSR Prolog (running as the Slurm user)
    * Creates Slurm HIL reserve reservation

  * ULSR Periodic Monitor (running as the Slurm user, or ```root```)

    * Detects reserve reservations which are not paired with release reservations
    * Interacts with the HIL client to reboot the nodes in the Slurm reserve
reservation, disconnect the nodes from all networks, and move the
nodes from the Slurm loaner project to the HIL free pool.
    * Creates Slurm HIL release reservation

If a failure is detected by the periodic monitor, the reserve
reservation will not be created, and the periodic monitor will retry
the HIL operations when scheduled to run again.  This retry process
will continue a long as the reserve reservation does not have a
matching release reservation.

To release nodes, as a Slurm non-privileged user run the following:
```
$ srun hil_release --reservation <HIL reserve reservation>
```

ULSR software actions:

  * Slurm Control Daemon ULSR Epilog
     * Detects 'hil_release' command and reservation in which the command was run
     * Deletes the Slurm HIL reserve reservation

  * ULSR Periodic Monitor
     * Detects release reservations which are not paired with reserve reservations
     * Interacts with the HIL client to reboots the nodes in the Slurm release
reservation, disconnect the nodes from all networks, and move the
nodes from the HIL free pool back to the Slurm loaner project.


## HIL Reservation Management Commands

The ```hil_reserve``` and ```hil_release``` commands are implemented
as ```bash(1)``` shell scripts, which do little more than cause the
```slurmctld``` prolog and epilog to run and communicate, via
their job names, that the user wishes to reserve or release HIL nodes.

These names are system reserved in that they are recognized by the
Slurm control daemon prolog and epilog as triggers for specific ULSR
reservation operations.

## Slurm Control Daemon Prolog and Epilog

The ```slurmctld``` prolog does some of the work required to place
nodes in a ULSR reservation.  The prolog consists of a ```bash```
script which invokes a common Python program used for both the prolog
and the epilog.  Prolog function is selected via an argument to the
Python script.  The epilog is implemented in an identical manner.

Likewise, some of The work required to release nodes from a HIL
reservation is performed by the ```slurmctld``` epilog.  As the
reservation to be released is in use at the time the prolog runs (it
is used to run the ```hil_release``` job), it is not possible to
delete the reservation in the prolog itself.

### Communication between Slurm Components

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

The Slurm control daemon prolog and epilog communicate ULSR
reservation state to the ULSR periodic monitor through the Slurm
reservations themselves.

## Periodic Reservation Monitor

The HIL reservation monitor runs periodically on the Slurm controller
node, as a ```cron(8)``` job, and looks for changes in Slurm HIL ULSR
reservations.  More specifically, the reservation monitor:

    * Looks for ULSR reserve reservations which do not have
      corresponding release reservations.  Each such Slurm reservation
      found represents a new ULSR reservation.

    * Looks for ULSR release reservations which do not have reserve
      reservations.  Each such Slurm reservation found identifies a
      ULSR reservation which has been released by the Slurm user.

For each singleton release reservation found, the HIL reservation
monitor:

  1. Invokes the HIL client API to move the nodes in the Slurm
  reservation between the free pool and the Slurm loaner project

  2. Creates or deletes the Slurm ULSR release reservation.

If the HIL client operations fail, the Slurm HIL release reservation
is either not created (```hil_reserve```) or left in place
(```hil_release```), so that the periodic reservation monitor can
retry the operation when scheduled again.


## HIL Client Interface

The HIL client interface connects the ULSR reservation monitor with
the HIL server, which in turn provides management and control over
compute and network resources available for loan between the Slurm
cluster and HIL end users. 

The HIL client is a separate package loaded onto the Slurm controller
node at ULSR software installation time.  

HIL client functions used by the ULSR reservation management software
include:
  * Node power on and off
  * Add a node to a HIL project, or remove a node from a HIL project
  * Connect a node to a network or disconnect node from a network

## Development Branching Strategy

The initial source code management strategy involves use of a single
Git repository and multiple, parallel development branches:

  1. The ```master``` branch is considered (relatively) stable and is
  used as the source for ULSR releases.

  2. The ```development``` branch is the common line of development
  and serves as both the source of, and merge destination for, feature
  development branches created and used by individual developers.

  3. Individual development branches, per-developer and/or
  per-feature, which merge back to the ```development`` branch. These
  should be named in a way which includes the owner's user ID.


# Software Installation

NOTE: The following assumes Slurm version 15 or greater is installed
and running in the cluster.   For background on Slurm installation
refer to the following links:

  * [How to Install Slurm on CentOS 7 Cluster](https://www.slothparadise.com/how-to-install-slurm-on-centos-7-cluster/)

  * [Slurm on CentOS 7](https://bitsanddragons.wordpress.com/2016/08/22/slurm-on-centos-7/)

The ULSR software is installed in four main steps:

  1. Clone the ULSR repository from GitHub onto the Slurm controller
  node
  2. Customize the installation Makefile, as required
  3. Run ```make install-controller``` on the Slurm controller node
  4. Run ```make install-server``` on each of the Slurm compute server nodes

## Clone ULSR Repository

```

```
## Edit Installation Makefile

The ULSR installation Makefile may be customized to align with the
target Slurm cluster configuration and administrative preferences.

The following variables (shown with default settings) may be modified
as necessary.

```
LOCAL_BIN = /usr/local/bin

SLURM_USER=slurm
SLURM_USER_DIR=/home/$SLURM_USER

INSTALL_USER=centos
INSTALL_USER_DIR=/home/$INSTALL_USER

SLURM_CONTROLLER = slurm-controller

NFS_SHARED_DIR = /shared
ULSR_SHARED_DIR = $(NFS_SHARED_DIR)/ulsr

SLURM_CONF_FILE=/etc/slurm/slurm.conf

ULSR_LOGFILE_DIR=/var/log/ulsr

PROLOG_LOGFILE_NAME = ulsr_prolog.log

MONITOR_LOGFILE_NAME = ulsr_monitor.log
```

NOTE: Changes to the Makefile variables above may require changes to
the ```common/hil_slurm_constants.py``` file to match.


## Install ULSR on the Slurm Controller Node

```
[root@slurm-controller ~]# git clone https://github.com/mghpcc-projects/user_level_slurm_reservations.git
[root@slurm-controller ~]# cd user_level_slurm_reservations
[root@slurm-controller ~]# make install-controller
```

Edit the ```slurm.conf``` file

### Slurm Control Daemon Prolog and Epilog Integration

For simplicity, the ULSR installation model assumes there are no other
Slurm control daemon prolog and epilog routines installed.  It may be
necessary to modify an existing Slurm control daemon prolog and
epilog installation hierarchy to additionally invoke the ULSR prolog
and epilog scripts.

## Install ULSR on the Slurm Compute Nodes

### Installation Makefile Transfer to Compute Nodes

During installation of ULSR on the Slurm controller node, the Makefile
will be copied to a directory exported via NFS.  This directory may
then be mounted by the Slurm compute nodes to provide direct access to
the installation Makefile.

Once the shared directory has been mounted, the Makefile may be copied
to a directory local to a compute node and passed as an argument to
```make```, or it may be referenced in place.

Alternatively, the Makefile may be copied to each compute node via
```scp(1)``` or other mechanism and passed to ```make(1)``` from its
destination location.

### Make Invocation

One each compute node, running as the root user, run ```make(1)``` and
pass the ULSR compute server installation target as an argument:

```
[root@slurm-compute1 ~]# cd /shared/ulsr
[root@slurm-compute1 ulsr]# make install-server
```
This will perform the following actions on the compute server:

  * Mount the directory NFS-exported by the Slurm controller ```$(NFS_SHARED_DIR)```
  * Create the Slurm user directory (```/home/$(SLURM_USER)```) and
```scripts``` subdirectory (this may not be necessary)
  * Copy the ```hil_reserve``` and ```hil_release``` commands from the
  NFS shared directory to the ```$(LOCAL_BIN)``` directory
  * Copy the ```slurm.conf``` file from the NFS shared directory to
the $(SLURM_CONF_FILE) directory.

At this point the Slurm compute server should be ready for use with
ULSR.


## HIL ULSR Periodic Monitor and Log File

The ULSR periodic monitor is scheduled as a ```cron(8)``` job on the
Slurm controller node.  The Slurm controller provisioning script
installs the periodic monitor wrapper script
```hil_slurm_monitor.sh``` in the ```$LOCAL_BIN``` directory, which
defaults to ```/usr/local/bin```.  The periodic monitor itself,
```hil_slurm_monitor.py``` is installed in the Slurm user
```scripts``` subdirectory.

After installation the ```crontab``` must be modified to invoke the
wrapper script periodically:
```
*/5 * * * * hil_slurm_monitor.sh
```
The above will invoke the monitor every five minutes.

## SlurmCtld Prolog and Epilog Installation

[UPDATE to reflect coexistence with other Slurm prolog / epilog modules]

If no other Slurm control daemon prolog and/or epilog is in use, the
SlurmCtld prolog and epilog must be specified in the ```slurm.conf``` file:

```
PrologSlurmctld=/<install_dir>/scripts/hil_slurmctld_prolog.sh
EpilogSlurmctld=/<install_dir>/scripts/hil_slurmctld_epilog.sh
```

These lines are added to the default ```slurm.conf``` by the Slurm
controller provisioning script.  The Slurm control daemon must be
restarted after the configuration change:

```
$ systemctl restart slurmctld.service
```

## HIL / ULSR Settings File

The ```common/hil_slurm_settings.py``` file contains constants used by
the ULSR software.  

### HIL Partition Name Prefix - HIL_PARTITION_PREFIX

The Slurm partition from which HIL nodes are reserved must be named in
a way which begins with the value of ```HIL_PARTITION_PREFIX```.  By
default this is set to:
```
HIL_PARTITION_PREFIX = 'HIL_partition'
```

### HIL Control Endpoint IP Address, User, and Password

```
HIL_ENDPOINT = "http://128.31.28.156:80"
HIL_USER = 'admin'
HIL_PW = <elided, see file>
```

### HIL Loaner Project Name
```
HIL_SLURM_PROJECT = 'slurm'
```

### Slurm Utility Installation Directory

This variable identifies the directory into which ```scontrol``` and
other Slurm commands have been installed prior to installation of the
ULSR software.
```
SLURM_INSTALL_DIR = '/usr/bin'
```

### ULSR Log Files
```
HIL_SLURMCTLD_PROLOG_LOGFILE = '/var/log/ulsr/hil_prolog.log'
HIL_MONITOR_LOGFILE = '/var/log/ulsr/hil_monitor.log'
```

## Compute Nodes Marked with HIL Feature

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



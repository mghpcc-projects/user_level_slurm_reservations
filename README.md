# MOC HIL User Level Slurm Reservations (ULSR)

V3.2  26-Mar-2018

# Introduction

ULSR software allows a non-privileged Slurm user to reserve Slurm
compute nodes for HIL operations, including bare-metal operations.
The nodes may be later released and returned to the pool of Slurm
compute nodes for use by others.

Two user-level commands, run in the Slurm batch scheduler environment,
manage ULSR node reservations:

  * ```hil_reserve```
  * ```hil_release```

These commands are executed as Slurm jobs via ```srun(1)``` and
```sbatch(1).```

Other software components perform HIL node management, Ethernet
network management, and Infiniband network management operations on
nodes reserved and freed using the above commands.  

The primary function of the ULSR software is to automate these
operations so that privileged user or administrator intervention is
not required.  The 

## Supported Targets

ULSR is supported on CentOS 7 on x86_64 systems, using Python 2.7 and
Slurm release 15 or greater.  It may work on Red Hat Enterprise Linux,
but it has not been tested in that distribution environment.

## Creating a Reservation

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
ReservationName=flexalloc_MOC_reserve_centos_1000_1498512332
StartTime=2017-06-26T21:25:32 EndTime=2017-06-27T21:25:32
Duration=1-00:00:00 Nodes=server1 NodeCnt=1 CoreCnt=1 Features=(null)
PartitionName=(null) Flags=MAINT,IGNORE_JOBS,SPEC_NODES,ALL_NODES
TRES=cpu=1 Users=centos Accounts=(null) Licenses=(null) State=ACTIVE
BurstBuffer=(null) Watts=n/a 
```
This is called the ULSR reserve reservation.  The name component
```1000``` corresponds to the UID of the ```centos``` user, whereas
the name component ```1498512332``` is the integer portion of the Unix
epoch time captured during reservation creation.

Some time later, after execution of the ULSR periodic monitor
(described in more detail below), a paired release reservation
similiar to the following should appear:

```
ReservationName=flexalloc_MOC_release_centos_1000_1498512630
StartTime=2017-06-26T21:30:30 EndTime=2018-06-27T21:30:29
Duration=365-00:00:00 Nodes=server1 NodeCnt=1 CoreCnt=1 Features=(null)
PartitionName=(null) Flags=MAINT,IGNORE_JOBS,SPEC_NODES,ALL_NODES
TRES=cpu=1 Users=centos Accounts=(null) Licenses=(null) State=ACTIVE
BurstBuffer=(null) Watts=n/a 
```

Note that the reserve and release reservations are for the same set of
nodes and overlap in time.  The Slurm scheduler allows this when the
```MAINT``` flag is specified during reservation creation.

## Releasing a Reservation

When finished, to release a HIL node, specify the ```hil_release```
command to ```srun(1)``` or ```sbatch(1)```, additionally specifying
the HIL reserve reservation name as the reservation in which to run
the job:

```
$ srun --reservation=flexalloc_MOC_reserve_centos_1000_1498512332 hil_release
```
This should ultimately remove both the reserve and release reservations.

Note that failure to specify ```--reservation=<name>``` as an argument
may cause the job to be queued, waiting for resources.  It is unlikely
to delete the reserve reservation or free the reserved nodes.

## Reservation Naming

ULSR reservations created using ```hil_reserve``` are named as follows:
```
flexalloc_MOC_reserve_<username>_<uid>_<Unix epoch time>
```
and
```
flexalloc_MOC_release_<username>_<uid>_<Unix epoch time>
```
An example:
```
flexalloc_MOC_reserve_centos_1000_1498497632
```
In the first case, the ```<Unix epoch time>``` corresponds to the
start time of the reservation, or approximately at the time the
```srun hil_reserve``` command is executed.

In the second case, the ```<Unix epoch time>``` is taken from the
corresponding reserve reservation.

## Slurm Reservation Creation

The ULSR reserve and release reservations are not created nor deleted
directly by the ```hil_reserve``` and ```hil_release``` commands.
Rather, the ULSR reservations are created and deleted *as a
consequence* of the user running the ```hil_reserve``` and
```hil_release``` commands.  

The actual creation and deletion operations are carried out on behalf
of the end user by Slurm control software, specifically a Slurm
control daemon prolog, a control daemon epilog, and a separate
periodic processor (```cron``` job) known as the ```ULSR monitor```.

## Restrictions on User Names and UIDs

Reservations are named after the user who invoked the ```srun
hil_reserve``` command.  The user's name and UID are passed to the
Slurmctld prolog and epilog through the ```SLURM_JOB_USER``` and
```SLURM_JOB_UID``` environment variables.

Priviliged users may specify the user ID with which to create ULSR
reservations by specifying the ```--uid=<name>``` argument.  It is
recommended that the ```srun``` and ```sbatch``` commands **not** be
specified with the ```--uid``` argument, however, as processing ULSR
reservations with alternate or additional user names has not been
tested.

At present, only the user named in the reservation may release the
reservation via ```hil_release```.  Of course, a privileged Slrum user
may update or delete Slurm / ULSR reservations using the
```scontrol``` command, **but the ULSR system state after such an
operation will be undefined and may pose a security risk**.
Furthermore, complete network restoration will likely require action
by system administrators.

## Reservation Start and End Times

The reserve and release reservation start times may differ from the
time at which the ```hil_reserve``` command is run.  This is because
reservations are created by the ```slurmctld``` prolog and epilog and
the ULSR periodic monitor only when the requested resources become
available and the job is scheduled for execution.

## Resource Sharing

Nodes placed in a Slurm HIL reservation are marked as exclusive and
may not be shared among users.

## Two-Screen Management Model

All HIL nodes are known, by common names, to the Slurm management
functions and to the HIL management functions.  The nodes must exist
in both the Slurm partition and the HIL partition simultaneously, in
advance of any ULSR reservation and release operations.

In the Slurm domain and, more specifically, in a Slurm partition nodes
marked with the ```HIL``` property and perhaps otherwise designated by
system administration may be thought of as either available 'for loan'
to HIL, or actually 'on loan' to a HIL. They are either available for
use in a HIL end user project, or are in use in a HIL end user project:

  * Nodes which have been placed in a ULSR reservation may be
    considered as 'on loan' to HIL.  In the HIL domain they may exist
    in a reserved HIL project, the HIL free pool, or in HIL end user
    project.

  * Nodes which are not in a ULSR reservation, but which are marked
    with the ```HIL``` property, may be considered as available for
    loan to HIL end user. They do not reside in the HIL free pool, but
    reside in a special HIL project.  This project is referred to as
    the 'ULSR project' or the 'ULSR loaner project'.

Once a Slurm node has been placed in a ULS reservation through the use
of ```hil_reserve```, it is necessary for the HIL end user to run HIL
management commands to cause the server node to fully participate in a
HIL user project.  The decription of these commands is beyond the
scope of this document.  Nevertheless, this requirement may be
interpreted as consistent with a 'two-screen' management model.


# HIL Project Operations

The Slurm gang scheduler schedules jobs among shared compute
resources.  By contrast, the Hardware Isolation Layer, or HIL,
automates allocation and management of bare-metal compute resources to
users.  As described, nodes which are eligible for loan via ULSR must
be part of a Slurm partition and a HIL cluster simultaneously.

ULSR control components interact with HIL to isolate nodes, including
from shared Ethernet networks.  From a HIL user's perspective, nodes
placed in or released from a ULSR reservation are moved between HIL
projects and the HIL free pool.

See [the HIL page](https://massopen.cloud/blog/project-hil/) for more
information on HIL.

# Network Operations

Generally, nodes placed in a ULSR reservation are isolated from
attached Ethernet and Infiniband networks.  Upon release, network
connections to ULSR nodes are restored to their prior state.

## Ethernet

Ethernet network management operations are performed by HIL on behalf
of the ULSR control software.  The ULSR control software initiates HIL
operations via the HIL client API.

For more information on HIL network management, refer to the [HIL
documentation](https://github.com/CCI-MOC/hil/blob/master/README.rst).

## Infiniband

By default, Infiniband network isolation and restoration operations
are performed by a set of separate, privileged utilities.  These are
implemented in a way which is designed to minimize the amount of
software which must be installed with elevated privileges.

These privileged utilities ultimately rely on [Linux RDMA / Infiniband
diags](https://github.com/linux-rdma) package utilities to perform
Infiniband device operations.  Specifically, the ```iblinkinfo(8)```
and ```ibportstate(8)``` commands are used.

Optionally, the ULSR control software (and Infiniband devices) may be
configured such that Infiniband diags utilities are invoked directly
by the ULSR control software, with requiring installation of the
privileged utilities.

By default, during a ULSR reserve operation, the Infiniband interfaces
on each reserved compute node will be shut down, by shutting down the
port of the attached Infiniband switch.  This blocks unauthorized
access to the Infiniband network by the ULSR node borrower.

Shutdown is accomplished by spawning a remote shell on each reserved
compute node and invoking the ```ibportstate ... disable``` command,
specifying the Infiniband links and switches which connect to the
compute node.

During such time as the ULSR reservation exists, initial Infiniband
network state is stored in an external database, as described below.

# Assumptions, Restrictions, Notes

Beyond any requirements imposed by the HIL node and network management
software and the Slurm batch scheduler, the following apply to the
ULSR software:

  1. All nodes in the HIL ULSR reservation pool must be previously
  configured into and present in a single Slurm partition.

  2. Slurm compute nodes must be marked with the ```HIL``` feature in
  order to be placed in a ULSR reservation.  Features are defined in
  the ```slurm.conf``` file or may be added to a node by a privileged
  user via the ```scontrol update``` command.  Refer to the [scontrol
  man page](https://slurm.schedmd.com/scontrol.html) for more
  information on using node features.

  3. The Slurm controller node in the partition is not available for
  HIL operations and is **not** marked with the ```HIL``` feature.

  4. Nodes may be released from a ULSR reservation through
  ```hil_release```, even though they are not up and running Linux.
  Some error messages may appear in the Slurmctld log file.  Note that
  detailed system behavior has not been fully evaluated and is likely
  to evolve over time.

  5. Python 2.7 must be installed on the Slurm controller node.

  6. The ```hil_reserve``` and ```hil_release``` commands must be
  available on both the Slurm controller node and on the compute nodes
  which form the target of the ULSR reservations. This is a
  requirement of the Slurm job scheduler and the ```sbatch(1)``` and
  ```srun(1)``` commands.  Distribution of ```hil_reserve``` and
  ```hil_release``` is accomplished during the ULSR software
  installation process.

# Logging

Slurm and the HIL reservation system maintain several log files which
archive system behavior.  These are:

  * The Slurm control daemon (```slurmctld```) running on the Slurm
    controller node writes to a log file, the location of which is
    defined by the ```SlurmctldLogFile``` parameter in the
    ```slurm.conf``` file.

  * HIL reservation operations performed by the Slurmctld prolog and
    epilog are logged to a file on the Slurm controller node.  The
    location of this file is configured in the
    ```ulsr_settings.py``` file.  By default, the location is
    ```/var/log/ulsr/ulsr_prolog.log```.

  * HIL reservation operations performed by the HIL periodic monitor
  are also logged to a file on the Slurm controller node.  The
  location of this file is configured in the
  ```ulsr_settings.py``` file.  By default, the location is
  ```/var/log/ulsr/ulsr_monitor.log```. 

  * The HIL server writes to ```/var/log/hil.log```.  Note the HIL
    server typically does not reside on the Slurm controller node.


# Implementation Details

## Software Components and Structure

The ULSR software running in the context of the Slurm partition
consists of the following:

  1. The ```hil_reserve``` and ```hil_release``` user commands
  described above.

  2. A dedicated Slurm control daemon prolog function, which runs in
  the context of the Slurm control daemon on the Slurm controller
  node.

  3. A periodic processor, scheduled by ```cron(8)```. This monitors
  Slurm ULSR reservations and performs HIL operations to move nodes
  between HIL user projects, the HIL free pool, the HIL ULSR loaner
  project.  The monitor also performs Infiniband control operations to
  isolate and restore loaned nodes on the Infiniband network.

  4. A MOC HIL client interface, used by the ULSR code to remotely
  execute HIL commands on the nodes placed into and freed from HIL
  reservations, and on the Ethernet switches terminating the physical
  network links which interconnect the nodes.

  5. An external database, used to maintain Infiniband network state
 during the time nodes are on loan.

  5. A Slurm partition instance.

  6. A MOC HIL cluster instance.


## Workflow and Functional Partitioning

The general workflow is as follows:

To reserve nodes, as a Slurm non-privilged user may run the following command:
```
$ srun hil_reserve
```
ULSR software actions:

  * Slurm Control Daemon ULSR Prolog (running as the Slurm user):
    * Creates ULSR reserve reservation

  * ULSR Periodic Monitor (running as the Slurm user, or ```root```):

    * Detects ULSR reserve reservations which are not paired with ULSR
release reservations 
    * Interacts with the HIL client to reboot the nodes in the ULSR reserve
reservation, disconnect those nodes from all networks, and move those
nodes from the Slurm loaner project to the HIL free pool.
    * Disables Infiniband network connections to each node.
    * Saves prior Infiniband network state in a database.
    * Creates the ULSR release reservation.

If a failure is detected by the periodic monitor, the reserve
reservation will not be created, and the periodic monitor will retry
the management operations when scheduled to run again.  This retry
process will continue a long as the reserve reservation does not have
a matching release reservation and as long as the reserve reservation
exists.

To release nodes, as a Slurm non-privileged user may run the following command:
```
$ srun hil_release --reservation <HIL reserve reservation>
```

ULSR software actions:

  * Slurm Control Daemon ULSR Epilog (running as the Slurm user):
     * Detects 'hil_release' command and the name of the reserve reservation in which the command was run 
     * Deletes the Slurm HIL reserve reservation

  * ULSR Periodic Monitor:
     * Detects release reservations which are not paired with reserve reservations
     * Interacts with the HIL client to reboot the nodes in the ULSR release
reservation, disconnect these nodes from all networks, and move these
nodes from the HIL free pool back to the Slurm loaner project.
     * Retrieves prior Infiniband network state from the database
     * Restores Infiniband network state.


## HIL Reservation Management Commands

The ```hil_reserve``` and ```hil_release``` commands are implemented
as ```bash(1)``` shell scripts, which do little more than cause the
```slurmctld``` prolog and epilog to run and communicate, via
their command names, that the user wishes to reserve or release ULSR nodes.

The command names are system reserved in that they are recognized by
the Slurm control daemon prolog and epilog as triggers for specific
ULSR reservation operations.

## Slurm Control Daemon Prolog and Epilog

The ```slurmctld``` prolog does some of the work required to place
nodes in a ULSR reservation.  The prolog consists of a ```bash```
script which invokes a common Python program used for both the prolog
and the epilog.  Prolog function is selected via an argument to the
Python script.  The epilog is implemented in an identical manner.

Likewise, some of the work required to release nodes from a ULSR
reservation is performed by the ```slurmctld``` epilog.  As the
reservation to be released is in use at the time the prolog runs (it
is used to run the ```hil_release``` job), it is not possible to
delete the reservation in the prolog itself.

### Communication between Slurm Components

The ```slurmctld``` prolog and epilog execution environment provides
very limited support for communication between the user, the user's
job, and the prolog and epilog.  For example, it is not possible for
the prolog or epilog to write status information to the user's TTY,
nor is is possible for the user's job to pass arguments to the prolog
or epilog.  While it may be possible to output information to the user
through a SPANK plugin, but that possibility is not considered further
here.

The name of the job submitted via ```srun``` or ```sbatch``` is
available to the prolog and epilog through a very limited set of
environment variables.  Also available in the environment are the user
name, user ID, and job node list.  Information regarding the Slurm
execution environment is available through subprocess execution of
various ```scontrol show``` commands, for example, ```scontrol show
job```.

Accordingly, the Slurm control daemon prolog and epilog communicate
ULSR reservation state to the ULSR periodic monitor through the Slurm
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


## Fault Detection and Recovery

Generally, the periodic reservation monitor will stop processing a
ULSR reservation upon encountering an error during a Slurm operation,
a HIL operation, or an Infiniband network operation.  

Reserve processing will stop before the corresponding release
reservation is created.  Likewise, release processing will stop before
the release reservation is deleted.  In this way, the monitor will
retry the failed operations when it is again scheduled to run.

Note this behavior will continue indefinitely; currently there is no
limit on the number of times the monitor will retry a reserve or
release operation.

<EOF>

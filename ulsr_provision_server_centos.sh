#!/usr/bin/env bash
#
# ulsr_provision_server.sh - MOC HIL ULSR Slurm Compute Server Provisioning Script
#
# Run on the controller node
# Installs MOC HIL User Level Slurm Reservations code
#
# Notes
#   Assumes Slurm has been previously installed or is installed separately
#   Assumes CentOS
#   Run as root on controller node, NOT on server nodes
#   NFS kernel server must be provisioned on the controller
#      /shared the shared directory, exported via NFS

set -x

SLURM_USER=slurm
SLURM_USER_DIR=/home/$SLURM_USER

INSTALL_USER=centos
INSTALL_USER_DIR=/home/$INSTALL_USER

SLURM_CONF_FILE_PATH=/etc/slurm
SLURM_CONF_FILE_NAME=slurm.conf
SLURM_CONF_FILE=$SLURM_CONF_FILE_PATH/$SLURM_CONF_FILE_NAME

PYTHON_VER=python2.7

DATE_TIME=`date +%Y%m%d_%H%M%S`

# Select proper release or Git repo

USE_ULSR_RELEASE=0

if [ $USE_ULSR_RELEASE = 1 ]; then
    ULSR_RELEASE_VERSION=0.0.3
    ULSR_DIR=$INSTALL_USER_DIR/ulsr-$ULSR_RELEASE_VERSION
    if [ -d $ULSR_DIR ]; then
	mv $ULSR_DIR $ULSR_DIR.$DATE_TIME
    fi
    mkdir -p $ULSR_DIR
else
    ULSR_BRANCH=development
    ULSR_DIR=$INSTALL_USER_DIR/ulsr-$ULSR_BRANCH
    if [ -d $ULSR_DIR ]; then
	mv $ULSR_DIR $ULSR_DIR.$DATE_TIME
    fi
    mkdir $ULSR_DIR
fi

SLURM_CONTROLLER=slurm-controller
NFS_SHARED_DIR=/shared
HIL_SHARED_DIR=$NFS_SHARED_DIR/hil

LOCAL_BIN=/usr/local/bin

yum makecache -y fast
yum install -y emacs
yum install -y nfs-utils
pip install https://github.com/pypa/virtualenv/tarball/master

echo "export SYSTEMD_EDITOR=emacs" >> ~/.bashrc

# Set up Python virtual environment, install Python hostlist

virtualenv -p $PYTHON_VER $SLURM_USER_DIR/scripts/ve
source $SLURM_USER_DIR/scripts/ve/bin/activate
pip install python-hostlist
deactivate

PYTHON_LIB_DIR=$ULSR_DIR/ve/lib/python2.7/site-packages

# Set up NFS server and shared FS, mount the Slurm controller shared dir

mkdir -p $NFS_SHARED_DIR
chmod 777 $NFS_SHARED_DIR
chown nobody:nobody $NFS_SHARED_DIR
sudo chkconfig nfs on
sudo service rpcbind start
sudo service nfs start

mount $SLURM_CONTROLLER:$NFS_SHARED_DIR $NFS_SHARED_DIR

cat >> /etc/fstab <<EOF
$SLURM_CONTROLLER:$NFS_SHARED_DIR nfs auto,noatime,nolock,bg,nfsvers=3,intr,tcp,actimeo=1800 0 0
EOF

# Create Slurm user script directory

mkdir -p $SLURM_USER_DIR/scripts
chown -R $SLURM_USER:$SLURM_USER $SLURM_USER_DIR/scripts

# Copy files to final resting places
#
# Install HIL user-level commands

HIL_COMMAND_FILES="hil_reserve \
                   hil_release"

for file in $HIL_COMMAND_FILES; do
    cp $HIL_SHARED_DIR/bin/$file $LOCAL_BIN
    chmod 755 $LOCAL_BIN/$file
done

# Update the Slurm config file

cp -p $HIL_SHARED_DIR/$SLURM_CONF_FILE_NAME $SLURM_CONF_FILE
chown $SLURM_USER:$SLURM_USER $SLURM_CONF_FILE

set +x

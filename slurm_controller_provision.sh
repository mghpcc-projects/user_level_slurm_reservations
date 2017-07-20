#!/usr/bin/env bash
#
# slurm_controller_provision.sh - SLURM MOC HIL Controller VM Provisioning Script
#
# Run on the controller node
# Installs Slurm, assumes no prior Slurm installation
#
# Notes
#   Assumes Ubuntu environment (16.04 LTS, YMMV)
#   Run as root on controller node, NOT on server nodes
#   NFS kernel server must be provisioned on the controller
#      /slurm is the shared directory, exported via NFS

set -x

echo "127.0.0.1 `hostname`" >> /etc/hosts

# Update the compute server node list and addresses in /etc/hosts as appropriate after 
# VM creation

echo "10.0.0.5 server1" >> /etc/hosts
echo "10.0.0.10 server2" >> /etc/hosts
echo "10.0.0.15 server3" >> /etc/hosts
echo "10.0.0.16 server4" >> /etc/hosts
echo "10.0.0.11 server5" >> /etc/hosts
echo "10.0.0.12 server6" >> /etc/hosts

apt-get update
apt-get -y install make
apt-get -y install gcc
apt-get -y install python2.7
ln -s /usr/bin/python2.7 /usr/bin/python
apt-get -y install emacs
apt-get -y install nfs-common
apt-get -y install nfs-kernel-server
apt-get -y install munge
apt-get -y install libmunge-dev
apt-get -y install virtualenv

echo "export SYSTEMD_EDITOR=emacs" >> ~/.bashrc

# Add the Slurm user, home directory, and system directories

useradd slurm 

mkdir -p /var/spool/slurmd.spool
chmod 755 /var/spool/slurmd.spool
chown slurm:slurm /var/spool/slurmd.spool

mkdir -p /var/log/slurm-llnl
chmod 755 /var/log/slurm-llnl
chown slurm:slurm /var/log/slurm-llnl

mkdir -p /var/run/slurm-llnl
chmod 755 /var/run/slurm-llnl
chown slurm:slurm /var/run/slurm-llnl

mkdir -p /var/spool/slurmd.spool
chmod 755 /var/spool/slurmd.spool
chown slurm:slurm /var/spool/slurmd.spool

mkdir -p /var/spool/slurm.state
chmod 755 /var/spool/slurm.state
chown slurm:slurm /var/spool/slurm.state

# NFS
# Export shared FS to compute nodes via NFS

mkdir /shared
chmod 777 /shared
chown nobody:nogroup /shared
sudo systemctl enable nfs-kernel-server

echo "/shared *(rw,sync,no_root_squash)" >> /etc/exports
exportfs -a

mkdir /shared/munge
chmod 700 /shared/munge
chown munge:munge /shared/munge

# Add Munge system directories and log file, create Munge key
# Export the Munge key for use by compute nodes

chmod 700 /etc/munge
chmod 711 /var/lib/munge
chmod 700 /var/log/munge
chmod 755 /var/run/munge

touch /var/log/munge/munged.log
chown munge:munge /var/log/munge/munged.log

echo "massopencloudajointprojectamonghubuniversities" > /etc/munge/munge.key

chmod 400 /etc/munge/munge.key
cp -p /etc/munge/munge.key /shared/munge

# Create package download directory and download required software

mkdir /opt/packages
cd /opt/packages

wget https://www.gnupg.org/ftp/gcrypt/libgpg-error/libgpg-error-1.27.tar.bz2
tar xvf libgpg-error-1.27.tar.bz2
cd libgpg-error-1.27
./configure
make install

cd /opt/packages

wget https://www.gnupg.org/ftp/gcrypt/libgcrypt/libgcrypt-1.7.8.tar.bz2
tar xvf libgcrypt-1.7.8.tar.bz2
cd libgcrypt-1.7.8
./configure
make install

cd /opt/packages

wget https://github.com/SchedMD/slurm/archive/slurm-17-02-6-1.tar.gz
tar xvf slurm-17-02-6-1.tar.gz
cd slurm-slurm-17-02-6-1
./configure
make install

# Python Hostlist

# cd /usr/local/lib/python2.7/site-packages
# wget https://www.nsc.liu.se/~kent/python-hostlist/python-hostlist-1.17.tar.gz
# tar xvf python-hostlist-1.17.tar.gz
# cd python-hostlist-1.17
# python setup.py build
# python setup.py install

# Install MOC HIL, including the slurm.conf file
# Export the slurm.conf file to server nodes

cd /opt/packages
wget https://github.com/mghpcc-projects/user_level_slurm_reservations/archive/moc-hil-v0.0.2.tar.gz
# tar xvf moc-hil-v0.0.2.tar.gz
tar xvf v0.0.2.tar.gz

# Install Slurm config file and copy to shared FS for use by compute nodes

cd user_level_slurm_reservations-0.0.2
# cd user_level_slurm_reservations-v0.0.3
cp -p ./test/slurm.conf /usr/local/etc/slurm.conf
cp -p ./test/slurm.conf /shared/slurm
chown slurm:slurm /usr/local/etc/slurm.conf

# Install HIL commands

cp commands/hil_reserve /usr/local/bin/
cp commands/hil_release /usr/local/bin/
chmod 755 /usr/local/bin/hil_reserve
chmod 755 /usr/local/bin/hil_release

# Install Slurm prolog and epilog under Slurm user home dir

mkdir -p /home/slurm/bin
mkdir -p /home/slurm/scripts
cd /home/slurm/scripts

virtualenv -p python2.7 ./ve

source ./ve/bin/activate
pip install python-hostlist

# Replace the following with a setup.py structure

cd ./ve/lib/python2.7/site-packages
cp /opt/packages/user_level_slurm_reservations-0.0.2/prolog/hil_slurm_constants.py .
cp /opt/packages/user_level_slurm_reservations-0.0.2/prolog/hil_slurm_logging.py .
cp /opt/packages/user_level_slurm_reservations-0.0.2/prolog/hil_slurm_helpers.py .
cp /opt/packages/user_level_slurm_reservations-0.0.2/prolog/hil_slurm_settings.py .
chown slurm:slurm ./hil_slurm*.py
deactivate

cp /opt/packages/user_level_slurm_reservations-0.0.2/prolog/hil_slurmctld_prolog.sh .
cp /opt/packages/user_level_slurm_reservations-0.0.2/prolog/hil_slurmctld_prolog.py .
cp /opt/packages/user_level_slurm_reservations-0.0.2/prolog/hil_slurmctld_epilog.sh .
chmod 755 /home/slurm/scripts/hil_slurmctld_prolog.sh
chmod 755 /home/slurm/scripts/hil_slurmctld_epilog.sh
chown -R slurm:slurm /home/slurm

# Install MOC HIL prerequisites
# Python Hostlist

# cd /usr/local/lib/python2.7/site-packages
# wget https://www.nsc.liu.se/~kent/python-hostlist/python-hostlist-1.17.tar.gz
# tar xvf python-hostlist-1.17.tar.gz
# cd python-hostlist-1.17
# python setup.py build
# python setup.py install

cd /opt/packages

# Munge again

/etc/init.d/munge start

# Slurm Daemon

/usr/local/bin/slurmctld & 

# Cleanup

rm -f /opt/packages/*.gz
rm -f /opt/packages/*.bz2

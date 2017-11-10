EUID = $(shell id -u -r)

HIL_CMDS = hil_reserve hil_release
LOCAL_BIN = /usr/local/bin

PROLOG_FILES = hil_slurmctld_prolog.py hil_slurmctld_prolog.sh hil_slurmctld_epilog.sh

MONITOR_FILES = hil_slurm_monitor.py hil_slurm_monitor.sh

NET_AUDIT_FILES =

LIB_FILES = hil_slurm_client.py hil_slurm_constants.py hil_slurm_helpers.py hil_slurm_logging.py hil_slurm_settings.py

DOCS = README.md LICENSE 

SLURM_USER = slurm
# SLURM_USER = tdonahue
SLURM_USER_DIR=/home/$(SLURM_USER)

INSTALL_USER = centos
INSTALL_USER_DIR=/home/$(INSTALL_USER)

SLURM_CONF_FILE_PATH = /etc/slurm
SLURM_CONF_FILE_NAME = slurm.conf
SLURM_CONF_FILE = $(SLURM_CONF_FILE_PATH)/$(SLURM_CONF_FILE_NAME)

PYTHON = python2.7
PYTHON_PKGS = python-hostlist requests git+https://github.com/cci-moc/hil.git@v0.2

VENV_SITE_PKG_DIR = $(SLURM_USER_DIR)/scripts/ve/lib/$(PYTHON)/site-packages

NFS_SHARED_DIR = /shared
ULSR_SHARED_DIR = $(NFS_SHARED_DIR)/ulsr
ULSR_LOGFILE_DIR = /var/log/ulsr

INSTALL = /usr/bin/install -m 755 -g $(SLURM_USER) -o $(SLURM_USER)


.PHONY: all install clean linux_packages nfs_share


all: install

install: check linux_packages nfs_share

	# ULSR log file directory
	mkdir -p $(ULSR_LOGFILE_DIR)
	chmod 755 $(ULSR_LOGFILE_DIR)
	chown $(SLURM_USER):$(SLURM_USER) $(ULSR_LOGFILE_DIR)

	# Virtual environment and support libraries
	mkdir -p $(SLURM_USER_DIR)/scripts
	virtualenv -p $(PYTHON) $(SLURM_USER_DIR)/scripts/ve
	source $(SLURM_USER_DIR)/scripts/ve/bin/activate
	pip install $(PYTHON_PKGS)
	deactivate

	# Copy common library modules
	$(INSTALL) $(LIB_FILES) $(VENV_SITE_PKG_DIR)

	# Copy HIL commands to local bin directory and NFS-shared bin directory
	$(INSTALL) $(HIL_CMDS) $(LOCAL_BIN)
	$(COPY) $(HIL_CMDS) $(ULSR_SHARED_DIR)/bin

	# Copy prolog and epilog scripts
	$(INSTALL) $(PROLOG_FILES) $(SLURM_USER_DIR)/scripts

	# Copy network audit scripts
	$(INSTALL) $(NET_AUDIT_FILES) $(SLURM_USER_DIR)/scripts

	# Update Slurm configuration file and share with compute nodes
	echo '# Slurmctld Prolog and Epilog' >> $(SLURM_CONF_FILE)
	echo 'PrologSlurmctld=$(SLURM_USER_DIR)/scripts/hil_slurmctld_prolog.sh' >> $(SLURM_CONF_FILE)
	echo 'EpilogSlurmctld=$(SLURM_USER_DIR)/scripts/hil_slurmctld_epilog.sh' >> $(SLURM_CONF_FILE)

	echo 'Provision Slurm compute nodes, then restart Slurm control daemon.'
	echo 'Installation complete.'

check:
	@if [[ $(EUID) -ne 0 ]] ; then echo 'Please run make as the root user' ; exit 1 ; fi

linux_packages: check
	yum makecache -y fast
	yum install -y emacs
	yum install -y nfs-utils
	yum install -y virtualenv

nfs_share: check
	mkdir -p $(NFS_SHARED_DIR)
	chmod 777 $(NFS_SHARED_DIR)
	chown nobody:nobody $(NFS_SHARED_DIR)
	chkconfig nfs on
	service rpcbind start
	service nfs start
	echo '$(NFS_SHARED_DIR) *(rw,sync,no_root_squash)' >> /etc/exports
	exportfs -a

	mkdir -p $(ULSR_SHARED_DIR)/bin
	chmod -R 700 $(ULSR_SHARED_DIR)/bin
	chown -R $(INSTALL_USER):$(INSTALL_USER) $(ULSR_SHARED_DIR)/bin

clean: check
	rm -rf $(SLURM_USER_DIR)/scripts
	rm -rf $(ULSR_LOGFILE_DIR)
	cd $(LOCAL_BIN)
	rm -f $(HIL_CMDS)

# EOF

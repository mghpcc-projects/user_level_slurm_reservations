# 
# Mass OpenCloud (MOC) / Hardware Isolation Layer (HIL)
# User Level Slurm Reservations (ULSR)
#
# Installation Makefile
#
# November 2017, Tim Donahue 	tpd001@gmail.com
#

HIL_CMDS = hil_reserve hil_release
LOCAL_BIN = /usr/local/bin

PROLOG_PY_FILES := hil_slurmctld_prolog.py
MONITOR_PY_FILES := hil_slurm_monitor.py
COMMAND_PY_FILES := $(PROLOG_PY_FILES) $(MONITOR_PY_FILES)

PROLOG_SH_FILES := hil_slurmctld_prolog.sh hil_slurmctld_epilog.sh 
MONITOR_SH_FILES := hil_slurm_monitor.sh
COMMAND_SH_FILES := $(PROLOG_SH_FILES) $(MONITOR_SH_FILES)

LIB_PY_FILES = hil_slurm_client.py hil_slurm_constants.py hil_slurm_helpers.py hil_slurm_logging.py hil_slurm_settings.py

DOCS = README.md LICENSE 

SLURM_USER := slurm
SLURM_USER_DIR=/home/$(SLURM_USER)

INSTALL_USER = centos
INSTALL_USER_DIR=/home/$(INSTALL_USER)

SLURM_CONTROLLER = slurm-controller

SLURM_CONF_FILE_PATH = /etc/slurm
SLURM_CONF_FILE_NAME = slurm.conf
SLURM_CONF_FILE = $(SLURM_CONF_FILE_PATH)/$(SLURM_CONF_FILE_NAME)

EUID := $(shell id -u -r)
SLURMCTLD_PID := $(shell (pgrep -u $(SLURM_USER) slurmctld))
SLURMD_PID := $(shell (pgrep -u $(SLURM_USER) slurmd))

PYTHON = python2.7
PYTHON_PKGS = python-hostlist requests git+https://github.com/cci-moc/hil.git@v0.2

VENV_SITE_PKG_DIR = $(SLURM_USER_DIR)/scripts/ve/lib/$(PYTHON)/site-packages

NFS_SHARED_DIR = /shared
ULSR_SHARED_DIR = $(NFS_SHARED_DIR)/ulsr

ULSR_LOGFILE_DIR = /var/log/ulsr
PROLOG_LOGFILE_NAME = ulsr_prolog.log
MONITOR_LOGFILE_NAME = ulsr_monitor.log

PROLOG_LOGFILE := $(ULSR_LOGFILE_DIR)/$(PROLOG_LOGFILE_NAME)
MONITOR_LOGFILE := $(ULSR_LOGFILE_DIR)/$(MONITOR_LOGFILE_NAME)

ULSR_COMMAND_PATH=/usr/bin:/usr/local/bin

INSTALL = /usr/bin/install -m 755 -g $(SLURM_USER) -o $(SLURM_USER)
SH = bash
COPY = cp


# Functions

define confirm-install
    @echo 'Unable to determine Slurm $(1) daemon PID.'
    @read -p 'Enter Y/y to force installation: ' -n 1 -r REPLY; echo; \
    [ $$REPLY = "y" ] || [ $$REPLY = "Y" ] || (exit 1;)
endef

# Confirm Slurm controller daemon is running or ask for install confirmation

define on-controller
    $(if $(SLURMCTLD_PID),\
	@echo 'Slurm control daemon PID is $(SLURMCTLD_PID)',\
	$(call confirm-install,'controller'))
endef

# Confirm Slurm (server) daemon is running or ask for install confirmation

define on-server
    $(if $(SLURMD_PID),\
	@echo 'Slurm daemon PID is $(SLURMD_PID)',\
	$(call confirm-install,'server'))
endef

# Verify we are running as root

define verify-root-user
    $(if $(filter $(EUID),0),@:,@echo 'Run `make $(MAKECMDGOALS)` as the root user'; exit 1)
endef

# Insert environment variable string into command .sh file
# Args:
#   1. subdir
#   2. file
#   3. env var name
#   4. value
define insert-var
    $(info $(1))
    $(info $(2))
    $(info $(3))
    $(info $(4))
    sed -i '/# Environment/a $(3)=$(4)' $(1)/$(2)
endef

# Build Targets

.PHONY: all install clean linux-packages controller-nfs-share server-nfs-share setup-cmd-env .FORCE

.FORCE:

setup-cmd-env: .FORCE
	$(foreach f, $(PROLOG_SH_FILES), $(call insert-var,commands,$(f),LOGFILE,$(PROLOG_LOGFILE)))
	$(foreach f, $(MONITOR_SH_FILES), $(call insert-var,commands,$(f),LOGFILE,$(MONITOR_LOGFILE)))
	$(foreach f, $(COMMAND_SH_FILES), $(call insert-var,commands,$(f),PATH,$(ULSR_COMMAND_PATH)))
	$(foreach f, $(COMMAND_SH_FILES), $(call insert-var,commands,$(f),HOME,$(SLURM_USER_DIR)))

all: install


install:
	@echo 'Run `make install-controller` as root to install ULSR on the Slurm controller node.'
	@echo 'Run `make install-server` as root to install ULSR on a Slurm compute server node.'
	@exit 1


# Install ULSR software on Slurm controller node

install-controller:
	@$(call verify-root-user)
	@$(call on-controller)
	@$(MAKE) linux-packages
	@$(MAKE) controller-nfs-share

	# ULSR log file directory
	@mkdir -p $(ULSR_LOGFILE_DIR)
	@chmod 755 $(ULSR_LOGFILE_DIR)
	@chown $(SLURM_USER):$(SLURM_USER) $(ULSR_LOGFILE_DIR)

	# Virtual environment and support libraries
	@mkdir -p $(SLURM_USER_DIR)/scripts
	@virtualenv -p $(PYTHON) $(SLURM_USER_DIR)/scripts/ve
	@$($(SH) ($(SLURM_USER_DIR)/scripts/ve/bin/activate; \
	          pip install $(PYTHON_PKGS); \
	          deactivate))

	# Copy common library modules
	@cd ./common && $(INSTALL) $(LIB_PY_FILES) $(VENV_SITE_PKG_DIR)

	# Insert environment variables into command .sh files
	@$(MAKE) setup-cmd-env

	# Copy HIL commands to local bin directory and NFS-shared bin directory
	@cd ./commands && $(INSTALL) $(HIL_CMDS) $(LOCAL_BIN)
	@cd ./commands && $(COPY) $(HIL_CMDS) $(ULSR_SHARED_DIR)/bin

	# Copy prolog, epilog, and monitor files beneath Slurm user dir
	@cd ./commands && $(INSTALL) $(COMMAND_PY_FILES) $(COMMAND_SH_FILES) $(SLURM_USER_DIR)/scripts

	# Copy network audit scripts
###	@cd ./netaudit && $(INSTALL) $(NET_AUDIT_FILES) $(SLURM_USER_DIR)/scripts

	# Update Slurm configuration file and share with compute nodes
	@echo '# Slurmctld Prolog and Epilog' >> $(SLURM_CONF_FILE)
	@echo 'PrologSlurmctld=$(SLURM_USER_DIR)/scripts/hil_slurmctld_prolog.sh' >> $(SLURM_CONF_FILE)
	@echo 'EpilogSlurmctld=$(SLURM_USER_DIR)/scripts/hil_slurmctld_epilog.sh' >> $(SLURM_CONF_FILE)
	@$(COPY) $(SLURM_CONF_FILE) $(ULSR_SHARED_DIR)/$(SLURM_CONF_FILE_NAME)

	# Share Makefile with compute nodes
	@$(COPY) Makefile $(ULSR_SHARED_DIR)

	@echo 'Provision Slurm compute nodes, then restart Slurm control daemon.'
	@echo 'Installation complete.'


# Install ULSR software on Slurm compute server node

install-server: 
	@$(call verify-root-user)
	@$(call on-server)
	@$(MAKE) linux-packages
	@$(MAKE) server-nfs-share

	# Create Slurm user script directory 
	@mkdir -p $(SLURM_USER_DIR)/scripts
	@chown -R $(SLURM_USER):$(SLURM_USER) $(SLURM_USER_DIR)/scripts

	# Copy HIL commands from NFS-shared bin directory to local bin directory 
	@$(INSTALL) $(ULSR_SHARED_DIR)/$(SLURM_CONF_FILE_NAME) $(SLURM_CONF_FILE)
	@cd $(ULSR_SHARED_DIR)/bin && $(INSTALL) $(HIL_CMDS) $(LOCAL_BIN)


linux-packages:
	@yum makecache -y fast
	@yum install -y emacs
	@yum install -y nfs-utils
	@yum install -y python-virtualenv


controller-nfs-share: linux-packages
	@mkdir -p $(NFS_SHARED_DIR)
	@chmod 777 $(NFS_SHARED_DIR)
	@chown nobody:nobody $(NFS_SHARED_DIR)
	@chkconfig nfs on
	@service rpcbind start
	@service nfs start
	@echo '$(NFS_SHARED_DIR) *(rw,sync,no_root_squash)' >> /etc/exports
	@-exportfs -a

	@mkdir -p $(ULSR_SHARED_DIR)/bin
	@chmod -R 700 $(ULSR_SHARED_DIR)/bin
	@chown -R $(INSTALL_USER):$(INSTALL_USER) $(ULSR_SHARED_DIR)/bin


server-nfs-share: linux-packages
	@mkdir -p $(NFS_SHARED_DIR)
	@chmod 777 $(NFS_SHARED_DIR)
	@chown nobody:nobody $(NFS_SHARED_DIR)
	@chkconfig nfs on
	@service rpcbind start
	@service nfs start
	@-mount $(SLURM_CONTROLLER):$(NFS_SHARED_DIR) $(NFS_SHARED_DIR)
	@echo '$(SLURM_CONTROLLER):$(NFS_SHARED_DIR) nfs auto,noatime,nolock,bg,nfsvers=3,intr,tcp,actimeo=1800 0 0'


clean:
	$(call verify-root-user)
	rm -rf $(SLURM_USER_DIR)/scripts
	rm -rf $(ULSR_LOGFILE_DIR)
	cd $(LOCAL_BIN)
	rm -f $(HIL_CMDS)
	rm -rf $(ULSR_SHARED_DIR)
# EOF

# Example-Python-Daemon

A systemd service implemented in Python and demonstrating SMAX communication.

Service structure is based on tutorials at https://alexandra-zaharia.github.io/posts/stopping-python-systemd-service-cleanly/ and https://github.com/torfsen/python-systemd-tutorial

This assumes that the service should run at the system level as smauser, with configuration files stored in `~smauser/wsma_config`.

Requires:
Development Tools group of RPM packages (on RHEL derived distros)
equivalent on Debian derived distros
    (this is in order to have the components needed to install systemd-python)
Systemd to be running
System package systemd-devel or equivalent (provides libsystemd)

Python packages:
systemd-python (in turn requires linux pacakage systemd-devel)
psutils
smax

Installation:
0. Install system level dependencies
1. Create conda environment accessible to smauser to operate the service in
2. Switch to conda environment.
3. Run pip install in base directory of package source to install the modules
4. Switch to `src/smax_daemon/`
5. Edit `on-start.sh` and `install.sh` to reflect the correct directories
6. Run `.install.sh` as root

Customization:
1. Bring your own hardware python module to daemonify, set up `pyproject.toml` to install it
2. Write the `daemon_config.json` file to define your SMA-X interface:
    table, key, values to be logged to SMA-X, SMA-X pub/sub control keys, and initial config values.
3. Implement your interface - see `example_hardware_interface.py` for details.
4. Edit the three lines at the top of `example_smax_daemon.py`
5. Customize `example_smax_daemon.service`
6. Customize `on_start.sh`
7. Customize `install.sh`

The logger level is set to debug by default. For production this should be turned down to warning.

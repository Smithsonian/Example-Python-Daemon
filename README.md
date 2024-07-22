# Example-Python-Daemon

A systemd service implemented in Python and demonstrating SMAX communication.

Service structure is based on tutorials at https://alexandra-zaharia.github.io/posts/stopping-python-systemd-service-cleanly/ and https://github.com/torfsen/python-systemd-tutorial

Service is set up to use `SIGINT` to safely stop the process.  This is caught with a `try/except` statement around the service event loop as `KeyboardInterrupt`, allowing closing of open pipes and files, and other shutdown procedures to be called.

Installation as both a user and system service is described in the second tutorial.

Requires:
Development Tools group of RPM packages (on RHEL derived distros)
equivalent on Debian derived distros
    (this is in order to have the components needed to install systemd-python)
Systemd to be running
Package systemd-devel
systemd-python (in turn requires linux pacakage systemd-devel)
psutils

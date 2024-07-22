#!/bin/bash

# >>> mamba initialize >>>
export MAMBA_EXE='/opt/mamba/bin/mamba';
export MAMBA_ROOT_PREFIX='/opt/mamba';

# -u: unbuffered output
$MAMBA_EXE activate example_smax_daemon
exec "/usr/local/lib/example_smax_daemon/example_smax_daemon.py"

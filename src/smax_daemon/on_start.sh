#!/bin/bash

# >>> mamba initialize >>>
export MAMBA_EXE='/opt/micromamba/bin/micromamba';
export MAMBA_ROOT_PREFIX='/opt/micromamba';

# -u: unbuffered output
$MAMBA_EXE run -n example_smax_daemon "/usr/local/lib/example_smax_daemon/example_smax_daemon.py"

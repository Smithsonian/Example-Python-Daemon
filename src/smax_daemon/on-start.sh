#!/bin/bash

# >>> mamba initialize >>>
export MAMBA_EXE='/opt/micromamba/bin/micromamba';
export MAMBA_ROOT_PREFIX='/opt/micromamba';

# -u: unbuffered output
$MAMBA_EXE run -n example-smax-daemon "/usr/local/lib/example-smax-daemon/example_smax_daemon.py"

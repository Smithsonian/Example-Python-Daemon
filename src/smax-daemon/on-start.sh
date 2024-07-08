#!/bin/bash
MAMBA_ROOT='/opt/miniforge3/'
source $MAMBA_ROOT/etc/profile.d/mamba.sh
conda activate $MAMBA_ROOT/envs/example-smax-daemon # change to your conda environment's name
# -u: unbuffered output
python -u /usr/local/lib/example-smax-daemon/example-smax-daemon.py

#!/bin/bash
source $HOME/anaconda3/etc/profile.d/conda.sh
conda activate smax # change to your conda environment's name
# -u: unbuffered output
python -u $HOME/.config/systemd/example-smax-daemon/example-smax-daemon.py

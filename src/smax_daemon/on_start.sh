#!/bin/bash

CONDA_PREFIX='/opt/mamba';
CONDA_ENV='example_smax_daemon';

eval "$CONDA_PREFIX/envs/$CONDA_ENV/bin/python example_smax_daemon.py"

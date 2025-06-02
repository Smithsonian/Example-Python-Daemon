#!/bin/bash

CONDA_PREFIX='/opt/miniforge3';
CONDA_ENV='example_smax_daemon';

eval "$CONDA_PREFIX/envs/$CONDA_ENV/bin/python example_smax_daemon.py"

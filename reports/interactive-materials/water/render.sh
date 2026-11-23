#!/bin/sh
cd "$(dirname "$0")" || exit 1
export PYTHONPATH="$HOME/repos/0911-video-edit-workprint/.venv/lib/python3.12/site-packages"
export OPENBLAS_NUM_THREADS=1
exec /usr/bin/python3 reflect.py

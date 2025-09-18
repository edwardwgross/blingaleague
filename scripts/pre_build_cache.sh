#!/usr/bin/env bash

BASE_DIR=/data/blingaleague
PYTHON=$BASE_DIR/environ/bin/python
LOG_FILE=$BASE_DIR/logs/pre_build_cache.log

echo "[`date`]" > $LOG_FILE

$PYTHON $BASE_DIR/manage.py pre_build_cache >> $LOG_FILE

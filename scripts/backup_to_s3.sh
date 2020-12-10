#!/usr/bin/env bash

BASE_DIR=/data/blingaleague
DB_BACKUP=$BASE_DIR/data/backup/blingaleague.sql
LOG_BACKUP=$BASE_DIR/logs/s3_backup.log

echo "[`date`]" >> $LOG_BACKUP

`mysqldump -ulivecommish -pSanderson2008 blingaleague > $DB_BACKUP` >> $LOG_BACKUP

aws s3 cp $DB_BACKUP s3://blingaleague-data01/ 2>&1 >> $LOG_BACKUP

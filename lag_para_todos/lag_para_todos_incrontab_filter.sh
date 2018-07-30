#!/bin/bash

# This is necessary because incrontab seems to run a single event when a file
# is modified. So we set up a trigger on the directory instead, and use this
# script to filter what's modified, and run lag_para_todos.sh only when the
# config file is updated.

if [ "${2}" = "lag_para_todos.config" ]
then
  /home/qadmin/lag_para_todos/lag_para_todos.sh "${1}${2}"
fi

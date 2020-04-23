#! /bin/sh
### BEGIN INIT INFO
# Provides:          lomushasho
# Required-Start:    networking
# Required-Stop:
# Default-Start:     2 3 4 5
# Default-Stop:      S 0 1 6
# Short-Description: Lo]v[ushasho QuakeLive Dedicated Server
# Description:       Lo]v[ushasho QuakeLive Dedicated Server
### END INIT INFO

set -e

GAME_PORT="27960"
RCON_PORT="28960"
SCREEN_NAME="quakelive"

get_pid() {
  echo "$(screen -list | grep ${SCREEN_NAME} | cut -d. -f1 | sed -e s/.//)"
}

do_start() {
  screen -S "${SCREEN_NAME}" -d -m \
    /home/qadmin/steamcmd/steamapps/common/qlds/run_server_x64_minqlx.sh \
      +set qlx_owner "76561198014448247" \
      +set net_strict 1 \
      +set net_port ${GAME_PORT} \
      +set sv_hostname "Lo]v[ushasho Dedicated QuakeLive Server" \
      +set fs_homepath /home/qadmin/quakelive \
      +set zmq_stats_enable 1 \
      +set zmq_stats_password "<PWD>" \
      +set zmq_stats_port ${GAME_PORT}
}

do_stop() {
  _PID="$(get_pid)"
  if [ "${_PID}" ]
  then
    echo "Killing PID ${_PID}"
    kill "${_PID}"
  fi
}

do_status() {
  _PID="$(get_pid)"
  if [ "${_PID}" ]
  then
    return 0
  else
    return 4
  fi
}

case "${1}" in
  start)
    get_pid
    do_start
  ;;
  stop)
    do_stop
  ;;
  restart|reload|force-reload)
    do_stop
    do_start
  ;;
  status)
    do_status
 ;;
 *)
  echo  "Usage: ${0} {start|stop|status|restart|reload|force-reload}"
  exit 1
 ;;
esac

exit 0

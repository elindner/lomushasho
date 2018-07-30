#!/bin/bash

FILE_NAME="${1}"
INTERFACE=eth0

print_rules() {
  tc qdisc show dev ${INTERFACE}
  tc filter show dev ${INTERFACE}
}

print_rules_and_exit() {
  echo ""
  echo "Final rules:"
  print_rules
  exit 0
}

remove_current_rules() {
  echo "Removing old rules..."
  tc qdisc del dev eth0 root 2> /dev/null
}

if [ "${EUID}" -ne 0 ]
then
  echo "This needs to be ran as root."
  exit 1
fi

if [ "${#}" -ne 1 ]
then
  echo "Illegal number of arguments. Need a file name or \"reset\"."
  exit 1
fi

echo "Current rules:"
print_rules
echo ""

if [[ "${1}" == "reset" ]]
then
  remove_current_rules
  print_rules_and_exit
fi

if [[ "${1}" == "print" ]]
then
  exit 0
fi

if [[ -z $(grep [^\ ] "${FILE_NAME}") ]]
then
  echo "Config file ${FILE_NAME} is empty. Clearing rules."
  remove_current_rules
  print_rules_and_exit
fi

remove_current_rules

tc qdisc add dev ${INTERFACE} root handle 1: prio bands 16 priomap 1 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0

handle=1
for ip_delay in $(cat ${FILE_NAME})
do
  IFS=':' read -r -a parts <<< "${ip_delay}"
  ip=${parts[0]}
  delay=${parts[1]}
  ip_hex=$(printf '%02x' ${ip//./ })
  handle=$((handle + 1))
  echo "Setting rule for ip ${ip} (${ip_hex}) with ${delay}ms delay (handle ${handle})..."

  tc qdisc add dev ${INTERFACE} handle ${handle}: parent 1:${handle} netem delay ${delay}ms
  tc filter add dev ${INTERFACE} pref ${handle} protocol ip u32 match ip dst ${ip} flowid 1:${handle}
done

print_rules_and_exit

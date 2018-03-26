#!/bin/bash
#
# ibendis.sh - TEST SUPPORT
#
LOGFILE=/var/log/ulsr/ulsr_monitor.log

function parseline() {
 local line;
 line=( ${1} ); nw=${#line[@]};
 if [ ${nw} == 2 ] || [ ${nw} == 3 ]; then
  ifld=0
  fld="${line[${ifld}]}"
  printf -v gvar '0x%14.14x' "${fld}" 2>/dev/null || { echo -E "# \"${fld}\"" "is not a valid GUID format."; exit 1; }
  printf 'GUID = \"%s\"\n' "${gvar}" >> ${LOGFILE}
  ifld=1
  fld="${line[${ifld}]}"
  printf -v pvar '%d' "${fld}" 2>/dev/null || { echo -E "# \"${fld}\"" "is not a valid port number format."; exit 2; }
  printf 'PORT NUMBER = \"%s\"\n' "${pvar}" >> ${LOGFILE}
  ifld=2
  fld="${line[${ifld}]}"
  printf -v pcmd '%s' "${fld}" 2>/dev/null || { echo -E "# \"${fld}\"" "is not a valid port action format."; exit 3; }
  printf 'ACTION = \"%s\"\n' "${pcmd}" >> ${LOGFILE}
 else 
  if [ ${line[0]} == "#" ]; then
   continue
  else
   echo "# Invalid input line" >> ${LOGFILE}
   exit 4
  fi
 fi
 parsedline=("${gvar}" "${pvar}" "${pcmd}")
}

echo "${0}" >> /var/log/ulsr/ulsr_monitor.log
while IFS= read -r line || [ -n "$line" ]
do
    parsedline=""
    parseline "${line}"
    echo "${parsedline[0]} ${parsedline[1]} ${parsedline[2]}"
    echo "  ${line}" >> ${LOGFILE}
done



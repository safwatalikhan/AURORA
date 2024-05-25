#!/bin/bash
ONLINE_REPORT_PROC="/home/wenyu2/data/cap-ret/parse-minitrace-and-report.py"
APP_UID_CHECKER="./check-app-uid.sh"
#APP_PACKAGE_NAME="$1"
#trace="$2"
#appLabel=$(aapt dump badging ${APP_PACKAGE_NAME}.apk | sed -n "s/^application-label:'\(.*\)'/\1/p" | awk '{print tolower($1)}'| sed 's/-//')
#OUT_DIR="test-logs/aurora-${appLabel}-${trace}/minitrace"


check_pos_int() {
	[[ "$1" =~ ^[0-9]+$ ]] && expr "$1" ">" "0" >/dev/null
}

get_mod_date() {
	adb shell stat -c %y "$1"
}

while true; do
	ret=$($APP_UID_CHECKER $1)
	if check_pos_int "$ret"; then
		export TEST_APP_UID="$ret"
		echo "APP_UID = $TEST_APP_UID"
	else
		echo "UID_CHECKER: $ret"
		sleep 5
		continue
	fi
	pids=$(adb shell ps | grep "$APP_PACKAGE_NAME" | tr -s ' ' | cut -f 2 -d ' ')
	if [[ -z "$pids" ]]; then
		echo "$APP_PACKAGE_NAME not running (PID_LIST = $pids), skip.."
		sleep 5
		continue
	fi
	curr_ts=$(date +%s)
	fp="/data/mini_trace_${TEST_APP_UID}_coverage.dat"
	adb shell truncate -s 0 "$fp"
	echo "PKG = $APP_PACKAGE_NAME; UID = ${TEST_APP_UID}"
	for pid in $pids; do
		if check_pos_int "$pid"; then
			echo "PID = $pid.."
			mod_time_before=$(get_mod_date "$fp")
			adb shell kill -USR2 "$pid"
			for i in $(seq 1 5); do
				sleep 0.5
				mod_time_after=$(get_mod_date "$fp")
				if [[ "$mod_time_before" != "$mod_time_after" ]]; then
					sleep 0.5
					break
				fi
				echo "#$i: No update"
			done
		fi
	done
	cov_fn="$OUT_DIR/cov-${curr_ts}.log"
	adb shell cat "$fp" >"$cov_fn"
	#[[ -f "$OUT_DIR/report-sock-fp" ]] && python3 "$ONLINE_REPORT_PROC" "$cov_fn" "$(cat '$OUT_DIR/report-sock-fp' | tr -d '[:space:]')"
	sleep 5
done

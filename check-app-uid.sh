#!/bin/bash

# ANDROID_SERIAL
# APP_PACKAGE_NAME
# TEST_APP_UID
# CTRL_PORT
#APP_PACKAGE_NAME="$1"
check_pos_int() {
	[[ "$1" =~ ^[0-9]+$ ]] && expr "$1" ">" "0" >/dev/null
}

# while true; do
# 	sleep 5
	CURR_APP_UID=$(adb shell stat -c '%U' "/data/data/$APP_PACKAGE_NAME" | tr -d '[:space:]' | xargs adb shell id -u | tr -d '[:space:]')
	if ! check_pos_int "$CURR_APP_UID"; then
		echo "Invalid app UID for $APP_PACKAGE_NAME on $ANDROID_SERIAL"
		# continue
		exit
	fi
	if [[ "$CURR_APP_UID" != "$TEST_APP_UID" ]]; then
		# echo "UID change detected: $TEST_APP_UID -> $CURR_APP_UID"
		TEST_APP_UID="$CURR_APP_UID"
		if [[ -z "$SKIP_MINITRACE" ]]; then
			for fn in "config.in" "coverage.dat" "data.bin" "info.log"; do
				fp="/data/mini_trace_${TEST_APP_UID}_${fn}"
				adb shell truncate -s 0 "$fp"
				adb shell chown "${TEST_APP_UID}:${TEST_APP_UID}" "$fp"
			done
			adb shell setenforce 0
		fi
	fi
	# `adb forward` is run anyway to avoid accidentally dropping forward settings.
	#adb forward "tcp:${CTRL_PORT}" "localabstract:edu.illinois.cs.ase.uianalyzer.p${TEST_APP_UID}"
	#[[ -z "$MINICAP_PORT" ]] || adb forward "tcp:${MINICAP_PORT}" localabstract:minicapx # Courtesy
	echo "$CURR_APP_UID"
# done

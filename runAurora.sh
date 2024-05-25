
export ANDROID_SDK_ROOT=/home/safwat/Android/Sdk
export APP_PACKAGE_NAME=$1
export appLabel=$(aapt dump badging ${APP_PACKAGE_NAME}.apk | sed -n "s/^application-label:'\(.*\)'/\1/p" | awk '{print tolower($1)}'| sed 's/-//')
export minutes=$2
export seconds=$((minutes*60))

#export trace=$3
screen_kill() {
	screen -S "$1" -p 0 -X stuff "^C"
}

for trace in 1 2 3
do
	{
	export OUT_DIR="test-logs/aurora-${appLabel}-${trace}"
	screen -dmS "emulatorRun-${trace}" emulator -avd Nexus_5_API_23 -no-snapshot-load -writable-system -wipe-data 
	sleep 30
	adb install Null_Keyboard.apk
	sleep 10
	adb shell ime enable com.wparam.nullkeyboard/.NullKeyboard
	sleep 2
	adb shell ime set com.wparam.nullkeyboard/.NullKeyboard
	sleep 2
	adb install ${APP_PACKAGE_NAME}.apk
	sleep 2
	adb shell monkey -p ${APP_PACKAGE_NAME} 1
	python2 login_scripts/auto-${appLabel}.py
	#sleep 10
	screen -dmS "miniTracing-${trace}" bash "gather-cov-and-cleanup.sh"
	#Restarting the app to ensure minitrace starts collecting traces
	#sleep 2
	adb shell am force-stop "${APP_PACKAGE_NAME}"
	sleep 1
	adb shell monkey -p "${APP_PACKAGE_NAME}" 1
	sleep 2
	#######################################################################
	
	#screen -dmS "minitracing" timeout ${minutes}m bash gather-minitrace-cov.sh ${APP_PACKAGE_NAME} ${trace}
	
	screen -L -dmS "auroraRun-${trace}" python Aurora.py ${minutes} ${APP_PACKAGE_NAME} ${trace} >> auroraLog.log
	
	sleep ${seconds}
	sleep 15
	adb shell pm clear ${APP_PACKAGE_NAME}
	sleep 30
	adb uninstall ${APP_PACKAGE_NAME}
	sleep 30
	adb -s emulator-5554 emu kill
	sleep 10
	cp screenlog.0 test-logs/aurora-${appLabel}-${trace}-main.log
	rm screenlog.0
	
	#Kill the current screens one at a time
	screen_kill "emulatorRun-${trace}"
	screen_kill "miniTracing-${trace}"
	screen_kill "auroraRun-${trace}"
	#cleanup 0
	} > >(ts "%Y/%m/%d %H:%M:%.S" | tee -a "test-logs/aurora-${appLabel}-${trace}.log") 2>&1
done
sleep 15
#killall screen

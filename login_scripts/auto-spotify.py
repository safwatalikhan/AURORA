#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import time
import subprocess

# 720p
DEV_ID = os.environ.get('ANDROID_SERIAL', 'emulator-5554')
USERNAME="vaveb94784@laserlip.com"
PASSWORD="Vaveb94784!"

def ADB_EXEC(cmd, sleep = 0):
	global DEV_ID
	os.system('adb -s ' + DEV_ID + ' shell ' + cmd)
	time.sleep(sleep)

def CURR_ACT():
	global DEV_ID
	return subprocess.check_output(['adb', '-s', DEV_ID, 'shell', 
		"dumpsys window windows | grep -E 'mCurrentFocus|mFocusedApp'"])

print 'Wait for the app to launch...'
#time.sleep(20)

retry = 0
while retry < 6:
	time.sleep(2)
	if 'com.spotify.mobile.android.service.LoginActivity' in CURR_ACT():
		break
	retry += 1

if retry >= 6:
	print '..not entering login activity'
	sys.exit(1)

print 'log in'
ADB_EXEC("input tap 500 1030", 0.5)
print 'username'
ADB_EXEC("input tap 500 460", 0.5)
ADB_EXEC("input text " + USERNAME, 0.5)
print 'password'
ADB_EXEC("input keyevent KEYCODE_TAB", 0.5)
# ADB_EXEC("input tap 500 350", 0.5)
ADB_EXEC("input text " + PASSWORD, 0.5)
print 'log in'
# ADB_EXEC("input keyevent KEYCODE_TAB", 0.5)
ADB_EXEC("input keyevent KEYCODE_ENTER", 5)

act = CURR_ACT()

if 'com.spotify.mobile.android.service.LoginActivity' in act:
	print '..wrong activity after login'
	sys.exit(1)

print 'done!'

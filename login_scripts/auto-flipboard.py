#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import time
import subprocess

# 720p screen resolution
USERNAME = 'vaveb94784@laserlip.com'
PASSWORD = 'Vaveb94784!'

def ADB_EXEC(cmd, sleep = 0):
	os.system('adb shell ' + cmd)
	time.sleep(sleep)

def CURR_ACT():
	return subprocess.check_output(['adb', 'shell', 
		"dumpsys window windows | grep -E 'mCurrentFocus|mFocusedApp'"])

ADB_EXEC("ime set com.wparam.nullkeyboard/.NullKeyboard", 2)

ime = subprocess.check_output(['adb', 'shell', "settings get secure default_input_method"])
print "softkb = %s" % str(ime)

if 'NullKeyboard' not in ime:
	print 'wrong keyboard..'
	sys.exit(1)

print 'Wait for the app to launch...'
#time.sleep(20)

retry = 0
while retry < 6:
	time.sleep(2)
	if 'FirstLaunchCoverActivity' in CURR_ACT():
		break
	retry += 1

if retry >= 6:
	print '..not entering login activity'
	sys.exit(1)

print 'get started..'
ADB_EXEC("input tap 500 1100", 2)
print 'email..'
ADB_EXEC("input tap 500 500", 2)
print 'email address..'
ADB_EXEC("input text " + USERNAME, 0.5)
ADB_EXEC("input tap 500 1100", 2)
print 'password..'
# ADB_EXEC("input tap 500 900", 0.5)
ADB_EXEC("input text " + PASSWORD, 0.5)
print 'log in..'
ADB_EXEC("input tap 500 1100", 20)

act = CURR_ACT()

if 'AccountLoginActivity' in act or 'FirstLaunchCoverActivity' in act:
	print '..wrong activity after login'
	sys.exit(1)

print 'done!'

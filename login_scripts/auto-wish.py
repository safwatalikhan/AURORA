
#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import time
import subprocess

# 720p
USERNAME="vaveb94784@laserlip.com"
PASSWORD="Vaveb94784!"

def ADB_EXEC(cmd, sleep = 0):
	os.system('adb shell ' + cmd)
	time.sleep(sleep)

def CURR_ACT():
	return subprocess.check_output(['adb', 'shell', 
		"dumpsys window windows | grep -E 'mCurrentFocus|mFocusedApp'"])

print 'Wait for the app to launch...'
#time.sleep(20)

retry = 0
while retry < 6:
	time.sleep(2)
	curr_act = CURR_ACT()
	if 'CredentialPickerActivity' in curr_act:
		ADB_EXEC("input keyevent KEYCODE_BACK", 0.5)
		break
	if 'CreateAccountActivity' in curr_act:
		print 'log in'
		ADB_EXEC("input tap 500 1070", 1)
		break
	if 'SignInActivity' in curr_act:
		break
	if 'LoginActivity' in curr_act:
		break
	retry += 1

if retry >= 6:
	print '..not entering login activity'
	sys.exit(1)

if 'CredentialPickerActivity' in curr_act:
	print 'go back from CredentialPickerActivity'
	ADB_EXEC("input keyevent KEYCODE_BACK", 3)

if 'LoginActivity' in curr_act:
	print 'log in'
	ADB_EXEC("input tap 380 800", 3)

# time.sleep(10)

print 'email / username'
ADB_EXEC("input tap 363 223", 0.5)
ADB_EXEC("input text " + USERNAME, 0.5)
ADB_EXEC("input tap 354 343", 0.5)
print 'password'
# ADB_EXEC("input keyevent KEYCODE_TAB", 0.5)
# ADB_EXEC("input tap 500 350", 0.5)
ADB_EXEC("input text " + PASSWORD, 0.5)
print 'sign in'
ADB_EXEC("input tap 372 428", 5)

act = CURR_ACT()

if 'SignInActivity' in act or 'login.LoginActivity' in act:
	print '..wrong activity after login'
	sys.exit(1)

print 'done!'

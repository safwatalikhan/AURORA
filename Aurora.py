#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import json
import pandas as pd
import random
import string
import bisect 
import AndroidTestingLibraryLocal as atl
import random
import math
import re
from collections import Counter
import torch
import time
import subprocess
import psutil
import ClassifyScreen as cs
import os
from os.path import join as pjoin
import datetime
import DataPreparation as dp
from DataPreparation import interactions


# In[ ]:


def Sort_Horizontally(tup):
    tup.sort(key = lambda c: (c.bounds[0][1]+c.bounds[1][1])/2)
    return tup


# In[ ]:


#Checks for clickable components and
#returns two lists: edittexts and buttons
def sortComponents(dc,device):
    clickable_components=dc.search_gui_components(device, event_type = atl.Tap)
    components=[]
    edittexts=[]
    buttons=[]
    for c in clickable_components:
        components.append(c)
        if "edittext" in c.component_class.lower():
            edittexts.append(c)
        elif "button" in c.component_class.lower():
            buttons.append(c)
    buttons=Sort_Horizontally(buttons)
    edittexts=Sort_Horizontally(edittexts)
    sorted_components=Sort_Horizontally(components)
    return sorted_components,buttons,edittexts


# In[ ]:


# Function to kill a process by specifying its pid
def kill(proc_pid):
    import time
    #Killing running processes in PC
    process = psutil.Process(proc_pid)
    for proc in process.children(recursive=True):
        proc.kill()
        #print("Killed one child process.")
    process.kill()
    process.terminate()
    print("\nKilled runApe() process from PC.")
    
    time.sleep(3)


# In[ ]:


# Copy and install APE
def initApe():
    # Copy ape.jar
    print("Installing ape...",end="\t")
    pushCommand="adb push ape/ape.jar /data/local/tmp/"
    push=subprocess.Popen(pushCommand.split(" "))    
    time.sleep(1)

    # Install ape
    installApeCommand="adb shell CLASSPATH=/data/local/tmp/ape.jar /system/bin/app_process /data/local/tmp/ com.android.commands.monkey.Monkey"
    installApe=subprocess.Popen(installApeCommand.split(" "))
    print("installation complete.")
    time.sleep(1)


# In[ ]:


# Connecting to the virtual device using Android Testing Library
def getDeviceInfo(): 
    dc = atl.DeviceConnector()
    device_list = dc.enumerate_discoverable_devices()

    device = dc.get_device(name = device_list[0].name, sdk_level=device_list[0].sdk_level)
    resolution=(device.screen_width,device.screen_height)
    return dc,device,resolution


# In[ ]:



# In[ ]:


# tarpitLabels=[0,7,10,13,19]


# In[ ]:


model=cs.initClassifierModel("Saved_Models//rico_screen_classifier_extenddata_acc81.pth")


# In[ ]:


import searchH
import loginH
import advertisementH
import playerH
import viewerH
import termsH
import onboardingH
import feedH
import typeH
import webH
import formH
import productH
import listH
def executeHeuristics(dc,device,preds,clickable_components,trace,logFile):
    startTimeAurora=time.time()
    def executeHeuristic(pred,clickable_components,logFile):
        if pred==0:
            return advertisementH.advertisementHeuristics(dc,device,logFile,trace,clickable_components)
        elif pred==3:
            return feedH.feedHeuristics(dc,device,logFile,clickable_components)
        elif pred==4:
            return formH.formHeuristics(dc,device,logFile,clickable_components)
        elif pred==6:
            return listH.listHeuristics(dc,device,logFile,clickable_components)
        elif pred==7:
            return loginH.loginHeuristics(dc,device,logFile,clickable_components)
        elif pred==9:
            return onboardingH.onboardingHeuristics(dc,device,logFile,clickable_components)
        elif pred==10:
            return playerH.playerHeuristics(dc,device,logFile)
        elif pred==11:
            return advertisementH.advertisementHeuristics(dc,device,logFile,trace,clickable_components)
        elif pred==12:
            return productH.productHeuristics(dc,device,logFile,clickable_components)
        elif pred==13:
            return searchH.searchHeuristics(dc,device,logFile,trace,clickable_components)
        elif pred==16:
            return termsH.termsHeuristics(dc,device,logFile,clickable_components)
        elif pred==18:
            return typeH.typeHeuristics(dc,device,logFile,trace,clickable_components)
        elif pred==19:
            return viewerH.viewerHeuristics(dc,device,logFile,clickable_components)
        elif pred==20:
            return webH.webHeuristics(dc,device,logFile,clickable_components)
        else:
            return 0
        
    heuristicPass=False
    for pred in preds:
        eh=executeHeuristic(pred,clickable_components,logFile)
        if eh!=0:
            actChange,ccChange=eh
            dp.updateLog(logFile,"Activity changed during heuristics: "+str(actChange),"heuristics")
            dp.updateLog(logFile,"Clickable components changed during heuristics: "+str(ccChange),"heuristics")
            if actChange>0 or ccChange>0:
                dp.updateLog(logFile,"Heuristic execution: PASSED","heuristics")
                heuristicPass=True
                break
            else:
                dp.updateLog(logFile,"Heuristic execution: FAILED","heuristics")
        
        
    if heuristicPass==False:
        # Restart the app
        appPackage=dc.get_current_app(device)
        dc.kill_app(device,appPackage)
        dc.launch_app(device,appPackage)
        dp.updateLog(logFile,"All predicted heuristics failed, restarted app.","heuristics")
        
    endTimeAurora=time.time()
    timeElapsed=endTimeAurora-startTimeAurora
    dp.updateLog(logFile,"RUNTIME: "+str(timeElapsed),"heuristics")
    print("Ended running heuristics, spent a total of ",(endTimeAurora-startTimeAurora)," seconds to run.")

# In[ ]:


def runApeUntilStuck(dc,device,appPackage,t_end):
    print("Started running: runApeUntilStuck().")
    initClickables=dp.getClickables(dc,device)
    print("Killing uiautomator-toller process in emulator.")
    #Killing uiautomator-toller process in emulator
    from ppadb.client import Client as AdbClient
    # Default is "127.0.0.1" and 5037
    client = AdbClient(host="127.0.0.1", port=5037)
    emu_device = client.device("emulator-5554")
    #Get the uid of tollerAutomator
    #So we can kill it during runtime for APE to run
    tollerAutomatorTuple=emu_device.shell("ps | grep com.github.uiautomator")
    if len(tollerAutomatorTuple)>0:
        tollerAutomatorPID=tollerAutomatorTuple.split()[1]
        emu_device.shell("kill "+tollerAutomatorPID)
        print("Killed uiautomator-toller process from emulator")
    
    #Run ape
    print("Running Ape.")
    startTime=time.time()
    runningMins=str(int((t_end-startTime)/60))
    runApeCommand="python ape/ape.py -p "+dc.get_current_app(device)+" --running-minutes "+runningMins+" --ape sata"
    print("Initializing",end="...\t")
    runApe=subprocess.Popen(runApeCommand, shell=True)
    print("Ape started running.")
    repeat=0
    diffAppScreens=0
    prevActivity=""
    timeUp=False
    
    while repeat<10 and diffAppScreens<10:
        if time.time()>=t_end:
            print("Time's up!")
            print("Ape will close now.")
            timeUp=True
            break
        activity = dc.get_current_activity(device)
        if activity==prevActivity:
            repeat+=1
        else:
            repeat=0
        #Count the number of times a different app screen appears
        if dc.get_current_app(device)!=appPackage:
            diffAppScreens+=1
        prevActivity=activity
        time.sleep(1)
    if not timeUp:
        print("Stuck on "+activity+" for more than 10 seconds.")
        print("Stopping Ape",end="...\t")
    else:
        print("Time's up for AURORA.")
    try:
        kill(runApe.pid)
        print("Ape stopped.")
   
    except:
        pass
    endTime=time.time()
    #Check if runApe process is still alive
    poll = runApe.poll()
    if poll is None:
        print("runApe() is still running!")
    else:
        print("runApe() is killed completely.")
    lastAppPackage=dc.get_current_app(device)
    lastAppAct=dc.get_current_activity(device)
    return timeUp,startTime,endTime

# In[1]:


import sys
runTime=int(sys.argv[1])
appPackage=sys.argv[2]
trace=sys.argv[3]

# runTime=10
# appPackage="flipboard.app"
# trace="6Test"

dc,device,resolution=getDeviceInfo()
appPackage=dc.get_current_app(device)
initApe()
systemStart=time.time()
labelMapping=json.load(open("labelMapping.json"))
t_end = time.time() + 60 * runTime

timeUp = False
apeTrace=[]

while time.time() < t_end or timeUp is False:
    #Run Ape until it is stuck for 10 seconds
    print("Entering main loop.")
    timeUp,startApe,endApe=runApeUntilStuck(dc,device,appPackage,t_end)
    if timeUp or time.time()>=t_end:
        break
    apeTrace.append((startApe,endApe,"APE"))
    
    if dc.get_keyboard_bounds(device):
        dc.send_event(device,atl.BackButton())
    #Classify screen
    #Show predictions
    sil,ss,hier,ocr,logPath,curtime=dp.getFilePaths(appPackage,trace)
    #Initialize the log file
    dp.updateLog(logPath,"APP: "+appPackage)
    
    #Getting clickable components and also saving dumpfile to hierPath
    clickable_components=dp.getClickables(dc,device,dumpFile=hier)
    dc.get_screen_capture(device,ss)
    dp.updateLog(logPath,"TIME: "+curtime)
    
    #Pre-check for troublesome screens
    #We preset login heuristics for Spotify and Wish login activities
    #This is done because they do not let us collect any screenshots on that particular screen
    #Or due to the added time (almost 20 seconds) in collecting UIHierarchy
    tApps=["com.spotify.music","com.contextlogic.wish"]
    tActs=["LoginActivity","SignInActivity"]
    if dc.get_current_app(device) != appPackage:
        dc.kill_app(device, appPackage)
        time.sleep(2)
        dc.launch_app(device, appPackage)
    if dc.get_current_app(device) in tApps and dc.get_current_activity(device) in tActs:
        preds=[7,7,7]
    else:
        #Get Silhouette json object and OCR text
        try:
            ocr,sil,tShapes,ntShapes=dp.createOCR_text_layout(ss,resolution)
            #Classifying screen
            preds=cs.classifyScreen(ss,sil,ocr,model,logPath)
        except:
            #In cases where our ocr mechanism fails, we treat them as viewer screens.
            #As most of these cases happen due to a full screen image with no visible clickable components
            preds=[19,19,19]
    predLabel1=labelMapping[str(preds[0])]
    predLabel2=labelMapping[str(preds[1])]
    predLabel3=labelMapping[str(preds[2])]
    print("Prediction for this screen:")
    print("1. "+predLabel1)
    print("2. "+predLabel2)
    print("3. "+predLabel3)
    
    #Running heuristics
    startTimeAurora=time.time()
    executeHeuristics(dc,device,preds,clickable_components,trace,logPath)
    endTimeAurora=time.time()
    timeElapsed=endTimeAurora-startTimeAurora
    dp.updateLog(logPath,"RUNTIME COMPLETE.","heuristics")
    print("Ended running heuristics, spent a total of ",(endTimeAurora-startTimeAurora)," seconds to run.")
    
systemEnd=time.time()
print("The full system ran for ",(systemEnd-systemStart)," seconds.")


# In[ ]:





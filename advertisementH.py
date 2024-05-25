#!/usr/bin/env python
# coding: utf-8

# In[1]:


import json
import pandas as pd
import random
import string
import bisect 
import AndroidTestingLibraryLocal as atl
import nltk
from nltk.corpus import wordnet
import random
import math
import re
from collections import Counter
import torch
import time
import subprocess
import numpy as np
from math import log
import re
import psutil
import time


# In[3]:


def Sort_Area(tup):
    tup.sort(key = lambda c: abs(c.bounds[0][1]-c.bounds[1][1])*abs(c.bounds[1][0]-c.bounds[0][0]))
    return tup


# In[4]:


# def kill(proc_pid):
#     process = psutil.Process(proc_pid)
#     for proc in process.children(recursive=True):
#         proc.kill()
#     process.kill()


# In[5]:


# clickable_components=dc.search_gui_components(device, event_type = atl.Tap)
# print("Found "+str(len(clickable_components))+" gui components.")
# clickable_components=Sort_Area(clickable_components)
# # print("Sorted the components according to component-area.")

# time.sleep(1)
# dc.send_event(device,atl.Tap(*clickable_components[1].center))
# print("Clicked on the Ad close button.")

# #### Let APE take over from here##############
# print("Waiting for Ad to close")
# time.sleep(5)
# # Copy ape.jar
# print("Installing ape...",end="\t")
# pushCommand="adb push ../ape/ape.jar /data/local/tmp/"
# push=subprocess.Popen(pushCommand.split(" "))    
# time.sleep(1)
# # Install ape

# installApeCommand="adb shell CLASSPATH=/data/local/tmp/ape.jar /system/bin/app_process /data/local/tmp/ com.android.commands.monkey.Monkey"
# installApe=subprocess.Popen(installApeCommand.split(" "))
# print("installation complete.")
# time.sleep(1)
# #Run ape
# runApeCommand="python ../ape/ape.py -p "+dc.get_current_app(device)+" --running-minutes 100 --ape sata"
# print("Initializing...",end="\t")
# runApe=subprocess.Popen(runApeCommand.split(" "), shell=True)
# print("Ape started running.")
# time.sleep(30)
# print("Stopping...",end="\t")
# kill(runApe.pid)
# print("Ape stopped.")


# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[6]:


# clickable_components=dc.search_gui_components(device, event_type = atl.Tap)
# print("Found "+str(len(clickable_components))+" gui components.")
# clickable_components=Sort_Area(clickable_components)
# print("The smallest is located on "+str(clickable_components[3].bounds))


# In[7]:


# dc.send_event(device,atl.Tap(*clickable_components[0].center))


# In[8]:


#Get screen metadata xml in temp.xml
# !adb shell uiautomator dump /sdcard/temp.xml
# !adb pull /sdcard/temp.xml temp.xml


# In[9]:


import DataPreparation as dp
from DataPreparation import interactions


# In[10]:


# def advertisementHeuristics(dc,device,logFile,clickable_components):
#     startActivity = dc.get_current_activity(device)
#     startCC=clickable_components
#     dp.updateLog(logFile,"ADVERTISEMENT","heuristics")
#     # If Aurora does not provide any components, then get them here using getClickables()
#     # Else take the components already provided
#     if len(clickable_components)<1:
#         clickable_components=dp.getClickables(dc,device)
#     print("Found "+str(len(clickable_components))+" gui components.")
#     clickable_components=Sort_Area(clickable_components)
#     # print("Sorted the components according to component-area.")

#     time.sleep(1)
#     interactions.pressButton(dc,device,clickable_components,clickable_components[0],logFile)
#     #dc.send_event(device,atl.Tap(*clickable_components[1].center))
#     print("Clicked on the Ad close button.")
    
#     endActivity= dc.get_current_activity(device)
#     endCC=dp.getClickables(dc,device,dumpFile="asdasd.xml")
#     actChange=(startActivity!=endActivity)
#     ccChange=dp.differentClickables(startCC,endCC)
#     return actChange,ccChange


# In[ ]:


def topLeftButtons(resolution,ntShapes):   
    topLeftRange=(int(resolution[0]*0.25),int(resolution[1]*0.25))
    topLeftButtons=[]
    for comp in ntShapes:
        b=tuple(comp[1])
        if b[0][0]<topLeftRange[0] and b[1][0]<topLeftRange[0] \
        and b[0][1]<topLeftRange[1] and b[1][1]<topLeftRange[1]:
            topLeftButtons.append(comp)
    if len(topLeftButtons)>0:
        x1=topLeftButtons[0][1][0][0]
        y1=topLeftButtons[0][1][0][1]

        x2=topLeftButtons[0][1][1][0]
        y2=topLeftButtons[0][1][1][1]
        
        area=int(abs(x2-x1)*abs(y2-y1))
        centerX=int((x1+x2)/2)
        centerY=int((y1+y2)/2)

        return centerX,centerY,area
    else:
        return None


# In[ ]:


def topRightButtons(resolution,ntShapes):   
    topRightRange=(int(resolution[0]*0.75),int(resolution[1]*0.25))
    topRightButtons=[]
    for comp in ntShapes:
        b=tuple(comp[1])
        if b[0][0]>topRightRange[0] and b[1][0]>topRightRange[0] \
        and b[0][1]<topRightRange[1] and b[1][1]<topRightRange[1]:
            topRightButtons.append(comp)
    if len(topRightButtons)>0:
        x1=topRightButtons[0][1][0][0]
        y1=topRightButtons[0][1][0][1]

        x2=topRightButtons[0][1][1][0]
        y2=topRightButtons[0][1][1][1]
        
        area=int(abs(x2-x1)*abs(y2-y1))
        centerX=int((x1+x2)/2)
        centerY=int((y1+y2)/2)

        return centerX,centerY,area
    else:
        return None


# In[ ]:


def findCrossButton(resolution,ntShapes):
    tl=topLeftButtons(resolution,ntShapes)
    tr=topRightButtons(resolution,ntShapes)
    crossCandidate=[]
    if tl is not None:
        print("Cross button found on the left.")
        print(tl)
        crossCandidate.append(tl)
    if tr is not None:
        print("Cross button found on the right.")
        print(tr)
        crossCandidate.append(tr)
        
    smallestArea=9999999
    chosenCand=None
    for cand in crossCandidate:
        if cand[2]<smallestArea:
            smallestArea=cand[2]
            chosenCand=cand

    return chosenCand


# In[ ]:


def advertisementHeuristics(dc,device,logFile,trace,clickable_components):
    aut=dc.get_current_app(device)
    startActivity = dc.get_current_activity(device)
    startCC=clickable_components
    dp.updateLog(logFile,"ADVERTISEMENT","heuristics")
    
    appPackage=dc.get_current_app(device)
    resolution=(device.screen_width,device.screen_height)
    silPath,ssPath,hierPath,ocrPath,logFile,curtime=dp.getFilePaths(appPackage,trace)
    dc.get_screen_capture(device,ssPath)
    ocrText,sil_cv,tShapes,ntShapes=dp.createOCR_text_layout(ssPath,resolution)    
    dp.updateLog(logFile,"APP: "+appPackage)
    dp.updateLog(logFile,"TIME: "+curtime)
    closeFound=False
    for t in tShapes:
        text=t[0] if t[0] is not None else ""
        if "close" in text.lower():
            cloudFound=True
            print("Close button found.")
            
            centerX=int((int(t[1][0][0])+int(t[1][1][0]))/2)
            centerY=int((int(t[1][0][1])+int(t[1][1][1]))/2)
            dc.send_event(device,atl.Tap(centerX,centerY))
            
    crossFound=False
    if not closeFound:
        clsBtn=findCrossButton(resolution,ntShapes)
        
        if clsBtn is not None:
            crossFound=True
            centerX,centerY,area=clsBtn
            print("Cross button at: ")
            print(centerX,centerY)
            dc.send_event(device,atl.Tap(centerX,centerY))

            
    
    if not crossFound:
        clickable_components=Sort_Area(clickable_components)
        # print("Sorted the components according to component-area.")
        if len(clickable_components)>0:
            interactions.pressButton(dc,device,clickable_components,clickable_components[0],logFile)
        else:
            dc.send_event(device,atl.Tap(int(resolution[0]/2),int(resolution[1]/2)))
            clickable_components=dp.getClickables(dc,device)
            clickable_components=Sort_Area(clickable_components)
            if len(clickable_components)>0:
                interactions.pressButton(dc,device,clickable_components,clickable_components[0],logFile)
            else:
                dc.send_event(device,atl.BackButton())
                if dc.get_current_app(device)!=aut:
                    dc.launch_app(device,aut)
            
        
        
    endActivity= dc.get_current_activity(device)
    endCC=dp.getClickables(dc,device,dumpFile="asdasd.xml")
    actChange=(startActivity!=endActivity)
    ccChange=dp.differentClickables(startCC,endCC)
    if not ccChange:
        dc.kill_app(device, aut)
        dc.launch_app(device,aut)
    time.sleep(2)
    endActivity= dc.get_current_activity(device)
    endCC=dp.getClickables(dc,device)
    actChange=(startActivity!=endActivity)
    ccChange=dp.differentClickables(startCC,endCC)
    return actChange,ccChange


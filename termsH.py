#!/usr/bin/env python
# coding: utf-8

# In[137]:


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
import psutil
import time


# In[3]:


import DataPreparation as dp
import TextPreparation as tp
from DataPreparation import interactions


# In[144]:


# dc = atl.DeviceConnector()
# device_list = dc.enumerate_discoverable_devices()

# device = dc.get_device(name = device_list[0].name, sdk_level=device_list[0].sdk_level)
# screen_width=device.screen_width
# screen_height=device.screen_height
# resolution=(screen_width,screen_height)
# resized_resolution=(144,256)
# clickable_components=dp.getClickables(dc,device)


# In[ ]:


def getArea(a):
    x1=a[0][0]
    y1=a[0][1]
    x2=a[1][0]
    y2=a[1][1]
    return abs(x1-x2)*abs(y1-y2)


# In[146]:


def termsHeuristics(dc,device,logFile,clickable_components):
    dp.updateLog(logFile,"Terms and Conditions","heuristics")
    actExplored = [dc.get_current_activity(device)]
    ccChanged=0
    def topLeftButtons(resolution,clickable_components):
        topLeftRange=(int(resolution[0]*0.25),int(resolution[1]*0.25))
        topLeftButtons=[]
        for comp in clickable_components:
            if "button" in comp.component_class.lower():
                b=comp.bounds
                if b[0][0]<topLeftRange[0] and b[1][0]<topLeftRange[0] \
                and b[0][1]<topLeftRange[1] and b[1][1]<topLeftRange[1]:
                    topLeftButtons.append(comp)
        if len(topLeftButtons)>0:
            return topLeftButtons[0]
        else:
            return None
        
    resolution=(device.screen_width,device.screen_height)
    legible_components=[comp for comp in clickable_components if getArea(comp.bounds)>0]
    tlBtn=topLeftButtons(resolution,legible_components)
    curTime=time.time()
    endTime=curTime+10
    while tlBtn is not None and time.time()<endTime:
        interactions.pressButton(dc,device,clickable_components,tlBtn,logFile)
        clickable_components=dp.getClickables(dc,device)
        legible_components=[comp for comp in clickable_components if getArea(comp.bounds)>0]
        tlBtn=topLeftButtons(resolution,legible_components)
    
    for comp in clickable_components:
        if "skip" in comp.resource_id.lower():
            interactions.pressButton(dc,device,clickable_components,comp,logFile)
            break
    
            
    act=dc.get_current_activity(device)
    if act not in actExplored: actExplored.append(act)
    newCC=dp.getClickables(dc,device)
    ccChange=dp.differentClickables(clickable_components,newCC)
    if ccChange: ccChanged+=1
    actChange=len(actExplored)-1
    return actChange,ccChanged


# In[ ]:





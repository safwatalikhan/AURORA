#!/usr/bin/env python
# coding: utf-8

# In[ ]:


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
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer


# In[ ]:


import DataPreparation as dp
import TextPreparation as tp
from DataPreparation import interactions


# In[ ]:


def getArea(a):
    x1=a[0][0]
    y1=a[0][1]
    x2=a[1][0]
    y2=a[1][1]
    return abs(x1-x2)*abs(y1-y2)
def getDim(a):
    width=abs(a[0][0]-a[1][0])
    height=abs(a[0][1]-a[1][1])
    return width,height


# In[ ]:


def randomInteraction(dc,device,bound):
    from DataPreparation import interactions
    x,y=(random.randint(bound[0][0],bound[1][0]),random.randint(bound[0][1],bound[1][1]))
    actions=["tap","swipe-up","swipe-down"]
    selAction=random.choice(actions)
    if selAction=="tap":
        print("tapping on",x,y)
        dc.send_event(device,atl.Tap(x,y))
        time.sleep(0.5)
    elif "swipe" in selAction:
        dx,dy=0,0
        if "up" in selAction:
            print("swiping up")
            dy=-500
        elif "down" in selAction:
            print("swiping down")
            dy=500
        
        dc.send_event(device, atl.Swipe(x,y,dx,dy,100))
        time.sleep(2)
        


# In[ ]:


def webHeuristics(dc,device,logFile,clickable_components):
    from DataPreparation import interactions
    import random
    aut=dc.get_current_app(device)
    actExplored = [dc.get_current_activity(device)]
    ccChanged=0
    
    dp.updateLog(logFile,"WEB","heuristics")
    resolution=(device.screen_width,device.screen_height)
    screenArea=resolution[0]*resolution[1]
    webComp=False
    clickable_components=dp.getClickables(dc,device)
    clickable_components=[comp for comp in clickable_components if getArea(comp.bounds)!=0]
    for comp in clickable_components:
        #Check if webview component covers 50% or more of the total screen area
        if "webview" in comp.component_class.lower() and (getArea(comp.bounds)/screenArea*100)>50:
            webComp=True


    if webComp:
        while i<10:
            randomInteraction(dc,device,clickable_components[-1].bounds)
            i+=1
    iconSizes=[(96,96),(72,72),(48,48),(36,36)]
    clickable_components=dp.getClickables(dc,device)
    icons=[comp for comp in clickable_components if getDim(comp.bounds) in iconSizes]
    counter=0
    while dc.get_current_activity(device)==actExplored[0] and counter<10 and len(icons)>0:
        dc.send_event(device,atl.Tap(*random.choice(icons).center))
        counter+=1
        time.sleep(0.5)

    time.sleep(2)
    dc.kill_app(device, aut)
    dc.launch_app(device,aut)
        
    act=dc.get_current_activity(device)
    if act not in actExplored: actExplored.append(act)
    newCC=dp.getClickables(dc,device)
    ccChange=dp.differentClickables(clickable_components,newCC)
    if ccChange: ccChanged+=1
    actChange=len(actExplored)-1
    return actChange,ccChanged


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
import numpy as np
from math import log
import re
import psutil
import time


# In[ ]:


import DataPreparation as dp
from DataPreparation import interactions


# In[ ]:


def area(a):
    width=abs(a[1][0]-a[0][0])
    height=abs(a[0][1]-a[1][1])
    return width*height


# In[ ]:


def Sort_Area(tup):
    tup.sort(key = lambda c: abs(c.bounds[0][1]-c.bounds[1][1])*abs(c.bounds[1][0]-c.bounds[0][0]))
    return tup


# In[ ]:


def onboardingHeuristics(dc,device,logFile,clickable_components):
    startActivity = dc.get_current_activity(device)
    startCC=clickable_components
    dp.updateLog(logFile,"ONBOARDING","heuristics")
    # If Aurora does not provide any components, then get them here using getClickables()
    # Else take the components already provided
    if len(clickable_components)<1:
        clickable_components=dp.getClickables(dc,device)
    print("Found "+str(len(clickable_components))+" gui components.")
    clickable_components=Sort_Area(clickable_components)
    # print("Sorted the components according to component-area.")

    time.sleep(1)
    try:
        interactions.pressButton(dc,device,clickable_components,clickable_components[0],logFile)
    except:
        pass
    #dc.send_event(device,atl.Tap(*clickable_components[1].center))
    print("Clicked on the close button.")
    
    endActivity= dc.get_current_activity(device)
    endCC=dp.getClickables(dc,device,dumpFile="asdasd.xml")
    actChange=(startActivity!=endActivity)
    ccChange=dp.differentClickables(startCC,endCC)
    return actChange,ccChange


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


def feedHeuristics(dc,device,logPath,clickable_components):
    startActivity = dc.get_current_activity(device)
    startCC=clickable_components
    dp.updateLog(logPath,"NEWS FEED","heuristics")
    # If Aurora does not provide any components, then get them here using getClickables()
    # Else take the components already provided
    if len(clickable_components)<1:
        clickable_components=dp.getClickables(dc,device)
        
    interactButtons=["comment","like"]
    curTime=time.time()
    endTime=curTime+15
    while time.time()<endTime:
        interactions.swipe(dc,device,clickable_components,"up",logPath)
        clickable_components=dp.getClickables(dc,device)
        for comp in clickable_components:
            if any([True for btn in interactButtons if btn in comp.text]):
                interactions.pressButton(dc,device,clickable_components,comp,logPath)
                clickable_components=dp.getClickables(dc,device)
    
    endActivity= dc.get_current_activity(device)
    endCC=dp.getClickables(dc,device)
    actChange=(startActivity!=endActivity)
    ccChange=dp.differentClickables(startCC,endCC)
    return actChange,ccChange
                
    


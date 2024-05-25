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
import TextPreparation as tp
from DataPreparation import interactions


# In[ ]:


def productHeuristics(dc,device,logPath,clickable_components):
    startActivity = dc.get_current_activity(device)
    startCC=clickable_components
    dp.updateLog(logPath,"PRODUCT","heuristics")
    
    
    
    def getImageViews(dc,device):
        clickable_components=dp.getClickables(dc,device)
        imageViews=[comp for comp in clickable_components if "imageview" in comp.component_class.lower() \
                   or "button" in comp.component_class.lower()]
        return imageViews
    
    iteration=0
    imageViews=getImageViews(dc,device)
    while len(imageViews)>0 and iteration<10:
        dc.send_event(device,atl.Tap(*random.choice(imageViews).center))
        imageViews=getImageViews(dc,device)
        iteration+=1
    
    endActivity= dc.get_current_activity(device)
    endCC=dp.getClickables(dc,device)
    actChange=(startActivity!=endActivity)
    ccChange=dp.differentClickables(startCC,endCC)
    return actChange,ccChange


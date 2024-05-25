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


def viewerHeuristics(dc,device,logFile,clickable_components):
    from DataPreparation import interactions
    import random
    actExplored = [dc.get_current_activity(device)]
    ccChanged=0
    
    dp.updateLog(logFile,"VIEWER","heuristics")
    dc.send_event(device,atl.BackButton())
        
    act=dc.get_current_activity(device)
    if act not in actExplored: actExplored.append(act)
    newCC=dp.getClickables(dc,device)
    ccChange=dp.differentClickables(clickable_components,newCC)
    if ccChange: ccChanged+=1
    actChange=len(actExplored)-1
    return actChange,ccChanged


# In[ ]:


# def viewerHeuristics(dc,device):
#     from DataPreparation import interactions
#     import random
#     actExplored = [dc.get_current_activity(device)]
#     ccChanged=0
    
#     dp.updateLog(logFile,"VIEWER","heuristics")
#     t_end=time.time()+60
    
#     while time.time()<t_end:
#         act,ccChange=action(dc,device,logFile,clickable_components)
        
#         if act not in actExplored: actExplored.append(act)
#         if ccChange: ccChanged+=1
            
#         clickable_components=dp.getClickables(dc,device)
#         random.shuffle(clickable_components)
        
#     act=dc.get_current_activity(device)
#     actChange=len(actExplored)-1
#     return actChange,ccChanged


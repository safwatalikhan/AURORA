#!/usr/bin/env python
# coding: utf-8

# In[2]:


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


# In[3]:


### SENTENCE SIMILARITY
#### https://towardsdatascience.com/bert-for-measuring-text-similarity-eec91c6bf9e1


# In[4]:


# !pip install sentence-transformers


# In[ ]:


import DataPreparation as dp
import TextPreparation as tp
from DataPreparation import interactions


# In[ ]:


def performTapOn(searchFor, searchOn, dc, device, logPath, actExplored, ccChanged,notInclude=""):
    clickable_components=dp.getClickables(dc,device)
    for comp in clickable_components:
        if searchOn=="class":
            attrib=comp.component_class.split(".")[-1].lower()
        elif searchOn=="rid":
            attrib=comp.resource_id.lower()
        elif searchOn=="text" or searchOn=="label":
            attrib=comp.text.lower()
        if notInclude:
            condition2=notInclude.lower() not in attrib.lower()
        else:
            condition2=True
        if searchFor.lower() in attrib.lower() and condition2:
            print("Tapping on:",end=" ")
            print(comp)
            act,ccChange=interactions.pressButton(dc,device,clickable_components,comp,logPath)
            if act not in actExplored: actExplored.append(act)
            if ccChange: ccChanged+=1
            print("Breaking out of performTapOn()")
            break

    return actExplored,ccChanged
    


# In[ ]:


def enterText(dc,device,logPath):
    import random
    lines=[]
    with open("wiki125k-words.txt","r") as word:
        for line in word.readlines():
            lines.append(line.replace("\n",""))
    text=lines[random.randint(0,len(lines)-1)]
    
    clickable_components=dp.getClickables(dc,device)
    for comp in clickable_components:
        if "edittext" in comp.component_class.split(".")[-1].lower():
            interactions.textField(dc,device,comp,text,logPath)
            break
    


# In[ ]:


def playerHeuristics(dc,device,logPath):
    from DataPreparation import interactions
    import random
    aut=dc.get_current_app(device)
    actExplored = [dc.get_current_activity(device)]
    ccChanged=0
    startTime=time.time()
    endTime=startTime+15
    dp.updateLog(logPath,"PLAYER","heuristics")
    if "music" in aut.lower():
        rand = atl.RandomStrategy(dc, device, aut)
        rand.execute(20,automatic_app_restart=False,direct=True)
        
    elif "main" in actExplored[-1].lower():
        actExplored,ccChanged=performTapOn("library", "rid", dc, device, logPath, actExplored, ccChanged)
        actExplored,ccChanged=performTapOn("button", "class", dc, device, logPath, actExplored, ccChanged,"imagebutton")
        enterText(dc,device,logPath)
        actExplored,ccChanged=performTapOn("create", "text", dc, device, logPath, actExplored, ccChanged)   
    elif "playing" in actExplored[-1].lower():
        actExplored,ccChanged=performTapOn("context", "rid", dc, device, logPath, actExplored, ccChanged)
        actExplored,ccChanged=performTapOn("artist", "text", dc, device, logPath, actExplored, ccChanged)
    elif "watch" in actExplored[-1].lower():
        clickable_components=dp.getClickables(dc,device)
        menuFound=False
        for i in range(2):
            if time.time()>endTime:
                break
            for comp in clickable_components:
                if "menu" in comp.resource_id.lower():
                    menuFound=True
                    break
            if not menuFound:
                dc.send_event(device,atl.BackButton())
                dp.updateLog(logPath,"Pressed back button.","heuristics")
            else:
                break
        
            
                
            
    return len(actExplored)-1,ccChanged
    


# In[14]:


def action(dc,device,logFile,clickable_components):
    import random
    r=random.randrange(1, 13)
    act,ccChange=dc.get_current_activity(device),False
    #Swiping randomly with a probability of 33%
    #Tapping with a probability of 67%
    if r%3==0:
        swipeDirection=["left","right"]
        act,ccChange=interactions.swipe(dc,device,clickable_components,random.choice(swipeDirection),logFile)
    else:
        buttonType=["play","next","prev","context","play","action","close"]
        for c in clickable_components:
            resID=tp.infer_spaces(c.resource_id.lower(),tp.wordcost,tp.maxword)
            if random.choice(buttonType) in resID:
                act,ccChange=interactions.pressButton(dc,device,clickable_components,c,logFile)
                return act,ccChange
    time.sleep(1)
                
    return act,ccChange


# In[15]:


import time
def playerHeuristics2(dc,device,logFile,clickable_components):
    from DataPreparation import interactions
    import random
    actExplored = [dc.get_current_activity(device)]
    ccChanged=0
    
    dp.updateLog(logFile,"PLAYER","heuristics")
    t_end=time.time()+15
    
    while time.time()<t_end:
        act,ccChange=action(dc,device,logFile,clickable_components)
        
        if act not in actExplored: actExplored.append(act)
        if ccChange: ccChanged+=1
            
        clickable_components=dp.getClickables(dc,device)
        random.shuffle(clickable_components)
        
    act=dc.get_current_activity(device)
    actChange=len(actExplored)-1
    return actChange,ccChanged


# In[ ]:





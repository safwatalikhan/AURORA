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


# In[ ]:


import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
def initSentenceTransformer():
    ##################################################
    # Store the column header embeddings beforehand, #     
    # so you only need to extract their vectors once #
    ##################################################
    infoCSV=pd.read_csv("info.csv")
    infocols=infoCSV.columns.tolist()
    model = SentenceTransformer('bert-base-nli-mean-tokens',device="cpu")
    infocols_embeddings=model.encode(infocols)
    ########################################################
    return model,infocols,infocols_embeddings,infoCSV


# In[ ]:


def getArea(a):
    x1=a[0][0]
    y1=a[0][1]
    x2=a[1][0]
    y2=a[1][1]
    return abs(x1-x2)*abs(y1-y2)


# In[ ]:


#Function to get the edit texts in sorted order (Top-Down)
def getEditTexts(dc,device):
    clickable_components=dp.getClickables(dc,device)
    editTexts=[comp for comp in clickable_components if "edittext" in comp.component_class.lower()]
    editTexts=sorted(editTexts, key=lambda x: (x.bounds[0][1]+x.bounds[1][1])/2, reverse=False)
    return editTexts


# In[ ]:


#Get all the components that are not (edittexts or submit button or has no labels)
def getNonEditTexts(dc,device,submitBtn):
    clickable_components=dp.getClickables(dc,device)

    nonEditTexts=[comp for comp in clickable_components if "edittext" not in comp.component_class.lower() \
                 and getArea(comp.bounds)!=0 and len(comp.text)>0 and comp.bounds != submitBtn.bounds]
    nonEditTexts=sorted(nonEditTexts, key=lambda x: (x.bounds[0][1]+x.bounds[1][1])/2, reverse=False)
    return nonEditTexts


# In[ ]:


def chooseOption(dc,device,comp,clickable_components,logPath):
    interactions.pressButton(dc,device,clickable_components,comp,logPath)
    
    curClick=dp.getClickables(dc,device)
    if dp.differentClickables(curClick,clickable_components):
        try:
            interactions.pressButton(dc,device,curClick,random.choice(curClick),logPath)
        except:
            pass
    else:
        pass
    


# In[ ]:


from numpy import unravel_index
#Function to get the button component based on the provided pressButtons array
def getPressButtonLikeComponent(buttons,pressButtons,model):
    buttonTexts=[]
    for b in buttons:
        bName=tp.infer_spaces(b.text.lower(),tp.wordcost,tp.maxword)
        buttonTexts.append(bName)
    buttonTexts_embedding=model.encode(buttonTexts)
    pressButtons_embedding=model.encode(pressButtons)
    similarityScores=cosine_similarity(
            buttonTexts_embedding[:],
            pressButtons_embedding[:]
        )
    
    max2dIndex=unravel_index(similarityScores.argmax(), similarityScores.shape)
    #print(buttonTexts)
    #print(similarityScores)
    return buttons[max2dIndex[0]]


# In[ ]:





# In[146]:


def formHeuristics(dc,device,logPath,clickable_components):
    startTime=time.time()
    startActivity = dc.get_current_activity(device)
    startCC=clickable_components
    dp.updateLog(logPath,"FORMS","heuristics")
    
    
    
    #Delete all existing texts in the edit text components
    editTexts=getEditTexts(dc,device)
    for comp in editTexts:
        interactions.textField(dc,device,comp,"",logPath)

    #Enter relevant texts in all of the edit text fields    
    model,infocols,infocols_embeddings,infoDF=initSentenceTransformer()
    myRow=infoDF[infoDF["app"]==dc.get_current_app(device)]
    editTexts=getEditTexts(dc,device)
    for comp in editTexts:
        if time.time()>(startTime+30):
            break
        similarity=cosine_similarity(model.encode([tp.infer_spaces(comp.text)]),infocols_embeddings)[0]
        try:
            inputText=str(myRow[infocols[np.argmax(similarity)]].tolist()[0])
        except:
            inputText="Test"
        interactions.textField(dc,device,comp,inputText,logPath,False)

    #Find the Submit button
    clickable_components=dp.getClickables(dc,device)
    submitBtn=getPressButtonLikeComponent(clickable_components,["complete","submit","done","sign up"],model)

    #Find all components that are not edittexts or the submit button
    # and select a random option from the dropdowns
    print("We will look for all the dropdowns and choose random options from there.",end="\n\n\n")
    nonEditTexts=getNonEditTexts(dc,device,submitBtn)
    while len(nonEditTexts)>0:
        if time.time()>(startTime+30):
            break
        print("Currently we have "+str(len(nonEditTexts))+" nonEditTexts.")
        selComp=nonEditTexts.pop(0)
        chooseOption(dc,device,selComp,clickable_components,logPath)

    print("We will press the submit button now.",end="\n\n\n")
    # Tap the submit button
    time.sleep(2)
    interactions.pressButton(dc,device,clickable_components,submitBtn,logPath)
    
    
    
    endActivity= dc.get_current_activity(device)
    endCC=dp.getClickables(dc,device)
    actChange=(startActivity!=endActivity)
    ccChange=dp.differentClickables(startCC,endCC)
    return actChange,ccChange


# In[ ]:





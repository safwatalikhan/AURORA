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


# In[ ]:


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
    searchCSV=pd.read_csv("searchStrings.csv")
    searchcols=searchCSV.columns.tolist()
    model = SentenceTransformer('bert-base-nli-mean-tokens')
    searchcols_embeddings=model.encode(searchcols)
    ########################################################
    return model,searchcols,searchcols_embeddings,searchCSV


# In[ ]:


import time
def searchHeuristics(dc, device,logPath,trace,clickable_components):
    actsExplored = [dc.get_current_activity(device)]
    cc=[clickable_components]
    infoDF=pd.read_csv("info.csv")
    searchDF=pd.read_csv("searchStrings.csv")
    aut=dc.get_current_app(device)

    clickable_components=dp.getClickables(dc,device)
    def searchForString(infoDF,searchDF,clickable_components,aut,searchBoxes,logPath):
        startTime=time.time()
        if len(searchBoxes)==0:
            return
        #Just in case we dont mention the category of the app-under-test in info.csv
        try:
            appCat=infoDF["category"][infoDF["app"]==aut]
            appCat=appCat.tolist()[0]
        except:
            dc.kill_app(device,aut)
            dc.launch_app(device,aut)
            return

        
        # For misc category, search string can be anything from any column
        # such as youtube app
        # For study app or dictionary app, choose a word from the dictionary randomly
        # For all the other apps, choose a value from the specific column that matches the category
        if appCat in ["misc","nan"]:
            randCol=random.choice(searchDF.columns.tolist())
            chooseFrom=searchDF[randCol].tolist()
        else:
            chooseFrom=searchDF[appCat].tolist()
        for box in searchBoxes:
            if time.time()>(startTime+15):
                break
            clickTry=0
            #Try clicking on the search box for at most 5 times
            # if the clickable elements change, carry on with the next steps
            while clickTry<3:
                print("ClickTry: ",clickTry)
                randomSearchString=random.choice(chooseFrom)
                interactions.textField(dc,device,box,randomSearchString,logPath,delExisting=True)
                curClickables=dp.getClickables(dc,device)
                if dp.differentClickables(clickable_components,curClickables):
                    break
                clickTry+=1
            clickable_components=dp.getClickables(dc,device)
            textViews=[comp for comp in clickable_components if "textview" in comp.component_class.lower() \
                      and comp.text.lower() not in ["thesaurus","dictionary","clear"]]


            if len(textViews)>0:
                print("Clicked on one of the search results.")
                curActivity,ccChange=interactions.pressButton(dc,device,clickable_components,random.choice(textViews),logPath)
                actsExplored.append(curActivity)
            else:
                #This part is necessary to get the OCR image in case ATL does not give us enough information
                print("ATL could not find any text views.")
                print("Looking for text views in OCR data.")
                resolution=(device.screen_width,device.screen_height)
                silPath,ssPath,hierPath,ocrPath,logPath,curtime=dp.getFilePaths(aut,trace)
                dc.get_screen_capture(device,ssPath)
                _,_,tShapes,ntShapes=dp.createOCR_text_layout(ssPath,resolution)
                ############################################################################################
                try:
                    ocrTextViews=[(int((s1[0]+s2[0])/2), int((s1[1]+s2[1])/2)) for t,(s1,s2) in tShapes \
                                 if t.lower() not in ["thesaurus","dictionary","clear"]]
                    print("OCR found these textviews: ")
                    print(ocrTextViews)
                    (x,y)=random.choice(ocrTextViews)
                    curActivity,ccChange=interactions.pressButtonNoComp(dc,device,clickable_components,x,y,logPath)
                    actsExplored.append(curActivity)
                except:
                    pass



    searchBoxes=[comp for comp in clickable_components if ("edittext" in comp.component_class.lower() or \
                         "search" in tp.infer_spaces(comp.resource_id)) and \
                 "voice" not in tp.infer_spaces(comp.resource_id) and \
                comp.text not in ["Thesaurus","Dictionary"]]

    #If there are no search boxes in sight, click on the search related button first
    # else type in the relevant searchString
    if len(searchBoxes)>0:
        print("Found some search boxes on screen.")
        searchForString(infoDF,searchDF,clickable_components,aut,searchBoxes,logPath)
    else:
        print("No search boxes on screen.")
        buttons=[comp for comp in clickable_components if "button" in comp.component_class.lower() \
                    and comp.text.lower() not in ["thesaurus","dictionary","clear"]]
        try:
            curActivity,ccChange=interactions.pressButton(dc,device,clickable_components,random.choice(buttons),logPath)
        except:
            if len(clickable_components)>0:
                curActivity,ccChange=interactions.pressButton(dc,device,clickable_components,random.choice(clickable_components),logPath)
            else:
                curActivity,ccChange=dc.get_current_activity(device),False
        actsExplored.append(curActivity)
        time.sleep(1)
        searchBoxes=[comp for comp in clickable_components if "edittext" in comp.component_class.lower() or \
                     "search" in tp.infer_spaces(comp.resource_id) and "voice" not in tp.infer_spaces(comp.resource_id)]
        searchForString(infoDF,searchDF,clickable_components,aut,searchBoxes,logPath)
    
    endActivity= dc.get_current_activity(device)
    cc.append(dp.getClickables(dc,device))
    ccChanged=dp.differentClickables(cc[0],cc[-1])
    actChanged=(len(list(set(actsExplored)))>1)
    
    return actChanged,ccChanged


# In[ ]:





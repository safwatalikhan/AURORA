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


from DataPreparation import interactions
from sentence_transformers import SentenceTransformer, util
from transformers import pipeline

#Summarizer is used to summarize the currently visible texts into a comment
summarizer = pipeline("summarization", model="stevhliu/my_awesome_billsum_model", max_length=20, min_length=5)

#Sentence transformer is used to find the "Type a comment..." kind of text box.
model = SentenceTransformer('all-MiniLM-L6-v2')


# In[ ]:


def typeHeuristics(dc,device,logFile,trace,clickable_components):
    startActivity = dc.get_current_activity(device)
    startCC=clickable_components
    dp.updateLog(logFile,"TYPE MESSAGE","heuristics")
    # If Aurora does not provide any components, then get them here using getClickables()
    # Else take the components already provided
    if len(clickable_components)<1:
        clickable_components=dp.getClickables(dc,device)
        
    appPackage=dc.get_current_app(device)
    resolution=(device.screen_width,device.screen_height)
    silPath,ssPath,hierPath,ocrPath,logPath,curtime=dp.getFilePaths(appPackage,trace)
    dc.get_screen_capture(device,ssPath)
    try:
        ocr,sil,tShapes,ntShapes=dp.createOCR_text_layout(ssPath,resolution)
        ocrText=[text for text,_ in tShapes if text is not None]
        #Initialize the log file
        dp.updateLog(logPath,"APP: "+appPackage)

        # Two lists of sentences
        sentences1 = ocrText

        sentences2 = ['Type your message']

        #Compute embedding for both lists
        embeddings1 = model.encode(sentences1, convert_to_tensor=True)
        embeddings2 = model.encode(sentences2, convert_to_tensor=True)

        #Compute cosine-similarities
        cosine_scores = util.cos_sim(embeddings1, embeddings2)

        #Output the pairs with their score
        max_cosine_score=-1
        max_cosine_index=0
        for i in range(len(sentences1)):
            for j in range(len(sentences2)):
                print("{} \t\t {} \t\t Score: {:.4f}".format(sentences1[i], sentences2[j], cosine_scores[i][j]))
                if cosine_scores[i][j]>max_cosine_score:
                    max_cosine_score=cosine_scores[i][j]
                    max_cosine_index=i
        print(sentences1[max_cosine_index])
        for t,s in tShapes:
            if t==sentences1[max_cosine_index]:
                typeX,typeY=int((s[0][0]+s[1][0])/2),int((s[0][1]+s[1][1])/2)

                comment=summarizer(' '.join(ocrText))[0]['summary_text']
                if len(comment)<1: comment="nice!"
                interactions.textFieldNoComp(dc,device,typeX,typeY,comment,logPath,delExisting=False)
                clickable_components=dp.getClickables(dc,device)
                sendButtons=[comp for comp in clickable_components if "button" in comp.component_class.lower()]
                for comp in sendButtons:
                    interactions.pressButton(dc,device,clickable_components,comp,logPath)
    except:
        
        pass

    
    
    endActivity= dc.get_current_activity(device)
    endCC=dp.getClickables(dc,device)
    actChange=(startActivity!=endActivity)
    ccChange=dp.differentClickables(startCC,endCC)
    return actChange,ccChange
                
    


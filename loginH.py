#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# Android Testing Library - gitlab repo
# https://gitlab.com/aami/android-testing-library 
# pip install -U AndroidTestingLibrary
# App installed from Google play store: 
# App name: Via.com


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


# In[ ]:


### SENTENCE SIMILARITY
#### https://towardsdatascience.com/bert-for-measuring-text-similarity-eec91c6bf9e1


# In[ ]:


# !pip install sentence-transformers


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
    infoCSV=pd.read_csv("info.csv")
    infocols=infoCSV.columns.tolist()
    model = SentenceTransformer('bert-base-nli-mean-tokens',device="cpu")
    infocols_embeddings=model.encode(infocols)
    ########################################################
    return model,infocols,infocols_embeddings,infoCSV
# Function to get a similar csv column to the input text
# This is used 
def getSimilarColumn(components,infocols,infocols_embeddings,model):
    import numpy as np
    from sklearn.metrics.pairwise import cosine_similarity

    editTexts=[]
    
    for e in components:
        if "edittext" in e.component_class.lower():
            eName=e.text.lower()+ " "+e.resource_id
            eName=tp.infer_spaces(eName,tp.wordcost,tp.maxword)
            editTexts.append(eName)
        else:
            editTexts.append("")
    
    emptyLabels=True
    for etext in editTexts:
        if len(etext)>0:
            emptyLabels=False
            break
    #If uihierarchy does not give us any labels
    #then we will assume that the first edittext is the username/email address field
    #and the next one is the password field
    if emptyLabels:
        return False

    editTexts_embeddings=model.encode(editTexts)
    similarityScores=cosine_similarity(
            editTexts_embeddings[:],
            infocols_embeddings[:]
        )
    matchingColumns=[]
    
    for s in similarityScores:
        matchingColumns.append(infocols[np.argmax(s)])

    return matchingColumns


# In[ ]:


#Get component-string pair list
def getEditTextStrings(editTexts,appPackage):
    compStringPairList=[]
    #Initializing sentence transformer before starting the exploration
    model,infocols,infocols_embeddings,infoCSV=initSentenceTransformer()
    #Get all the edittext components in one list
    matchingColumns=getSimilarColumn(editTexts,infocols,infocols_embeddings,model)
    for i,column in enumerate(matchingColumns):
        if appPackage in infoCSV['app'].tolist():
            appIndex=infoCSV['app'].tolist().index(appPackage)
            compStringPairList.append((editTexts[i],infoCSV[column][appIndex]))
        else:
            compStringPairList.append((editTexts[i],infoCSV[column][random.randint(0,len(infoCSV)-1)]))
    
    return compStringPairList
    


# In[ ]:


#Get the button coordinate that we need to tap and tap on it
#any button containing label related to the given buttonText 
def tapButton(dc,device,resolution,buttonText,clickable_components):
    def getButtons(buttonText,buttons):
        coords=[]
        buttonFound=False

        for comp in buttons:
            if comp.text is not None:
                componentInfo=comp.text.lower()
                componentInfo=tp.infer_spaces(componentInfo,tp.wordcost,tp.maxword)
                for txt in buttonText:
                    if txt in componentInfo:
                        buttonFound=True
                        coord=comp.center
                        coords.append(coord)
        if not buttonFound:
            dc.get_screen_capture(device,"temp.jpg")
            ocr,sil,tShapes,ntShapes=dp.createOCR_text_layout("temp.jpg",resolution)
            for t in tShapes:
                for txt in buttonText:
                    if t[0] is not None:
                        if txt in tp.infer_spaces(t[0].lower(),tp.wordcost,tp.maxword):
                            buttonFound=True
                            coord=tuple(map(lambda i, j: int((i + j)/2), t[1][0], t[1][0]))
                            coords.append(coord)
        return coords
    
    buttons=[comp for comp in clickable_components if "edittext" not in comp.component_class.lower()]
    coords=getButtons(buttonText,buttons)
    for coord in coords:
        dc.send_event(device,atl.Tap(*coord))
        time.sleep(1)
        clickable_components2=dp.getClickables(dc,device,dumpFile="test.dump")
        if dp.differentClickables(clickable_components,clickable_components2):
            return
        


# In[ ]:


def loginHeuristics(dc,device,logPath,clickable_components=[]):
    prev_clickables=clickable_components
    resolution=(device.screen_width,device.screen_height)
    appPackage=dc.get_current_app(device)
    #Getting clickable components and also saving dumpfile to hierPath
    clickable_components=dp.getClickables(dc,device)
    ssPath=logPath.replace(".log",".jpg")
    dc.get_screen_capture(device,ssPath)
    curtime=str(int(time.time()))
    dp.updateLog(logPath,"TIME: "+curtime)

    #Get Silhouette json object and OCR text
    try:
        ocr,sil,tShapes,ntShapes=dp.createOCR_text_layout(ssPath,resolution)
    except:
        return loginHeuristics3(dc,device,logPath,clickable_components)
    editTexts=[comp for comp in clickable_components if "edittext" in comp.component_class.lower()]
    
    
    actExplored = [dc.get_current_activity(device)]
    ccChanged=0
    startCC=clickable_components
    dp.updateLog(logPath,"LOGIN","heuristics")     


    #Remove all existing strings in the edit texts
    for component in editTexts:
        dc.send_event(device,atl.Tap(*component.center))
        #Delete existing text
        dc.send_event(device,atl.MoveEnd())
        dc.send_event(device,atl.LongBackSpace())

    #Getting clickable components and also saving dumpfile to hierPath
    clickable_components=dp.getClickables(dc,device)
    dc.get_screen_capture(device,ssPath)
    dp.updateLog(logPath,"TIME: "+curtime)

    #Get Silhouette json object and OCR text
    ocr,sil,tShapes,ntShapes=dp.createOCR_text_layout(ssPath,resolution)
    editTexts=[comp for comp in clickable_components if "edittext" in comp.component_class.lower()]

    #If the current screen has only one EditText
    if len(editTexts)==1:
        #Get EditComponent-String pair for the only textfield
        etComp,text=getEditTextStrings(editTexts,appPackage)[0]
        #Enter the string in the EditComponent
        if etComp.text!=text:
            try:
                interactions.textField(dc,device,etComp,text,logPath,True)
            except:
                interactions.textField(dc,device,etComp,"text",logPath,True)

        #Tap on the button that has one of the buttonTexts
        buttonText=["next","continue"]
        tapButton(dc,device,resolution,buttonText,clickable_components)
        time.sleep(0.5)

        #Check for new components and enter password in the password field
        clickable_components=dp.getClickables(dc,device)
        editTexts=[comp for comp in clickable_components if "edittext" in comp.component_class.lower()]
        etStringPairs=getEditTextStrings(editTexts,appPackage)
        for etComp,text in etStringPairs:
            if "password" in etComp.resource_id.lower():
                interactions.textField(dc,device,etComp,text,logPath,False)
                time.sleep(0.5)
                break

        #Check for new components again, find the login button and tap on it
        clickable_components=dp.getClickables(dc,device)
        buttonText=["login","log in","sign in","signin"]
        tapButton(dc,device,resolution,buttonText,clickable_components)
        time.sleep(0.5)
    elif len(editTexts)==2:
        etStringPairs=getEditTextStrings(editTexts,appPackage)
        for etComp,text in etStringPairs:
            if text!=etComp.text:
                interactions.textField(dc,device,etComp,text,logPath)
        buttonText=["login","log in","sign in","signin","start"]
        tapButton(dc,device,resolution,buttonText,clickable_components)
    elif len(editTexts)==3:
        buttonText=["log in", "login"]
        tapButton(dc,device,resolution,buttonText,clickable_components)
        time.sleep(0.5)
        clickable_components=dp.getClickables(dc,device)
        editTexts=[comp for comp in clickable_components if "edittext" in comp.component_class.lower()]
        etStringPairs=getEditTextStrings(editTexts,appPackage)
        for etComp,text in etStringPairs:
            interactions.textField(dc,device,etComp,text,logPath)
        buttonText=["login","log in","sign in","start"]
        tapButton(dc,device,resolution,buttonText,clickable_components)
        
    act=dc.get_current_activity(device)
    if act not in actExplored: actExplored.append(act)
    curClickables=dp.getClickables(dc,device)
    if dp.differentClickables(curClickables,clickable_components): ccChanged+=1
    actChange=len(actExplored)-1
    
    return actChange,ccChanged
            
            


# In[ ]:


def getPersonInfo(dc,device,info):
    appPackage=dc.get_current_app(device)
    credApps=info['app'].tolist()
    loginEntryIndex=credApps.index(appPackage)
    signupEntryIndices=[x for x in range(len(credApps)) if x is loginEntryIndex]
    signupEntryIndex=random.choice(signupEntryIndices)
    return info.loc[signupEntryIndex]


# In[ ]:


# Commented out due to its inability to handle components with empty labels
# Function to get a similar csv column to the input text
# This is used 
def getSimilarColumn(components,infocols,infocols_embeddings,model):
    editTexts=[]
    
    for e in components:
        if "edittext" in e.component_class.lower():
            eName=e.text.lower()+ " "+e.resource_id
            eName=tp.infer_spaces(eName,tp.wordcost,tp.maxword)
            editTexts.append(eName)
        else:
            editTexts.append("")
    #print(editTexts)
    editTexts_embeddings=model.encode(editTexts)
    similarityScores=cosine_similarity(
            editTexts_embeddings[:],
            infocols_embeddings[:]
        )
    matchingColumns=[]
    
    for s in similarityScores:
        matchingColumns.append(infocols[np.argmax(s)])
    return matchingColumns
    


# In[ ]:


def getLoginButton(clickable_components,loginButtonText,stModel):
    hiSimilarity=-1
    loginButton=""
    for i,comp in enumerate(clickable_components):
        compClass=comp.component_class.split(".")[-1].lower()
        compResID=comp.resource_id.lower()
        if ("button" in compClass or (compResID and "textview" in compClass)) and comp.tappable:
            compText=comp.text.lower()
            compText=tp.infer_spaces(compText,tp.wordcost,tp.maxword)
            similarity=cosine_similarity(stModel.encode([compText]),stModel.encode(loginButtonText))[0]
            print(compText)
            print(similarity)
            if similarity.max()>hiSimilarity:
                hiSimilarity=similarity.max()
                loginButton=comp
    return loginButton


# In[ ]:


from numpy import unravel_index
def getPressButtonLikeComponent(buttons,pressButtons,model):
    buttonTexts=[]
    for b in buttons:
        bName=tp.infer_spaces(b.text.lower()+" "+b.resource_id,tp.wordcost,tp.maxword)
        buttonTexts.append(bName)
    print("buttonTexts: ",end="\t")
    print(buttonTexts)
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


def loginHeuristics1(dc,device,logFile,clickable_components=[]):
    loginButtonText=["login","log in","sign in","signin","start"]
    appPackage=dc.get_current_app(device)
    if appPackage=="flipboard.app":
        return loginHeuristics2(dc,device,logFile,clickable_components=[])
        
    actExplored = [dc.get_current_activity(device)]
    ccChanged=0
    startCC=clickable_components
    dp.updateLog(logFile,"LOGIN","heuristics")       
    def refreshComponents(dc,device):
        clickable_components=dp.getClickables(dc,device)
        sorted_components,buttons,edittexts=dp.sortComponents(clickable_components)
        return sorted_components,buttons,edittexts
    

    
    def fillText(sorted_components,personInfo):
        model,infocols,infocols_embeddings,infoCSV=initSentenceTransformer()
        csvColumns=getSimilarColumn(sorted_components,infocols,infocols_embeddings,model)
        #If getSimilarColumn() fails due to empty labels
        if not csvColumns:
            #Separate the edittext components
            editTexts=[]
            for comp in sorted_components:
                if "edittext" in comp.component_class.lower():
                    editTexts.append(comp)
        #print("sorted components length: ",len(sorted_components))
        for i,component in enumerate(sorted_components):
            print("working with ="+component.resource_id+", "+component.component_class+", "+component.text.lower())
            if "edittext" in component.component_class.lower():
                print("Got an edit text.",end="\t")
                try:
                    print(component.resource_id)
                except:
                    print()
                print("Going to choose from:",end=" ")
                print(csvColumns)
                col=csvColumns[i]
                inputText=str(personInfo[col])
                interactions.textField(dc,device,component,inputText,logFile)
            #Spinner heuristic, other heuristics can also be added later
            elif "spinner" in component.component_class.lower():
                #print("Got a spinner.")
                interactions.spinner(dc,device,component,logFile)
                
    
     
    #Get screen dimensions
    width=device.screen_width
    height=device.screen_height

    #Get sentence transformer model and embeddings for the csv columns
    model,infocols,infocols_embeddings,info=initSentenceTransformer()

    #Get login/signup info from info.csv
    personInfo=getPersonInfo(dc,device,info)
    

    
    # If Aurora does not provide any components, then get them here using getClickables() and sort them
    if len(clickable_components)<1:
        clickable_components=dp.getClickables(dc,device)
        
    sorted_components,buttons,edittexts=dp.sortComponents(clickable_components)
    
    
    # If there are more than or less than 2 edittexts
    #then we cannot just enter email and password
    #we need to find the login button and get to the 2-edittext screen
    if len(edittexts)!=2:
        print("Could not find 2 edittexts, searching for login button.")
        loginButton=getLoginButton(sorted_components,loginButtonText,model)
        print("Found login button to be: "+str(loginButton))
        act,cc=interactions.pressButton(dc,device,clickable_components,loginButton,logFile)
            
    sorted_components,buttons,edittexts=refreshComponents(dc,device)
    fillText(sorted_components,personInfo)
    loginButton=getLoginButton(sorted_components,loginButtonText,model)
    print("Printing the login button that we found:",end=" ")
    print(loginButton)
    print("Login button bounds: ",loginButton.bounds)
    #dc.send_event(device,atl.Tap(*loginButton.center))
    act,cc=interactions.pressButton(dc,device,clickable_components,loginButton,logFile)
        #return
        
    #We wait for upto 5 seconds incrementally and check if activity has changed
    for i in range(5):
        act=dc.get_current_activity(device)
        if act!=actExplored[-1]:
            break
        else:
            time.sleep(1)
    if act not in actExplored: actExplored.append(act)
    if cc: ccChanged+=1
    act=dc.get_current_activity(device)
    actChange=len(actExplored)-1
    
    return actChange,ccChanged
            
            


# In[ ]:


#Simple heuristics for logging into apps through serial input
def loginHeuristics2(dc,device,logFile,clickable_components=[]):
    actExplored = [dc.get_current_activity(device)]
    ccChanged=0
    
    
    startCC=clickable_components
    dp.updateLog(logFile,"LOGIN","heuristics")
    
    infoCSV=pd.read_csv("info.csv")
    row=getPersonInfo(dc,device,infoCSV)
    email=row["email address"]
    password=row["password"]
    clickable_components=dp.getClickables(dc,device)
    for comp in clickable_components:
        if "email" in comp.text.lower() and "textview" in comp.component_class.split(".")[-1].lower():
            act,ccChange=interactions.pressButton(dc,device,clickable_components,comp,logFile)
            if act not in actExplored: actExplored.append(act)
            if ccChange: ccChanged+=1
            break
    time.sleep(500/1000)
    dc.send_event(device, atl.Text(email))
    clickable_components=dp.getClickables(dc,device)
    for comp in clickable_components:
        if "next" in comp.text.lower() and "textview" in comp.component_class.split(".")[-1].lower():
            act,ccChange=interactions.pressButton(dc,device,clickable_components,comp,logFile)
            if act not in actExplored: actExplored.append(act)
            if ccChange: ccChanged+=1
            break
    time.sleep(500/1000)
    dc.send_event(device, atl.Text(password))
    time.sleep(500/1000)
    for comp in clickable_components:
        if "button" in comp.resource_id.lower():
            act,ccChange=interactions.pressButton(dc,device,clickable_components,comp,logFile)
            if act not in actExplored: actExplored.append(act)
            if ccChange: ccChanged+=1
            break
    
    actChange=len(actExplored)-1
    return actChange,ccChanged
                
    


# In[ ]:


def loginHeuristics3(dc,device,logFile,clickable_components=[]):
    startActivity = dc.get_current_activity(device)
    actExplored = [startActivity]
    ccChanged=0
    startCC=clickable_components
    dp.updateLog(logFile,"LOGIN","heuristics")
    def canLogin(dc,device,info):
        appPackage=dc.get_current_app(device)
        credApps=info['app'].tolist()
        try:
            loginEntryIndex=credApps.index(appPackage)
            return True,loginEntryIndex
        except:
            return False,-1
        
    def refreshComponents(dc,device):
        clickable_components=dp.getClickables(dc,device)
        sorted_components,buttons,edittexts=dp.sortComponents(clickable_components)
        return sorted_components,buttons,edittexts
    
    def getPersonInfo(dc,device,info,doLogin,loginEntryIndex):
        credApps=info['app'].tolist()
        if doLogin:
            return info.loc[loginEntryIndex]
        else:
            signupEntryIndices=[x for x in range(len(credApps)) if x is not loginEntryIndex]
            signupEntryIndex=random.choice(signupEntryIndices)
            return info.loc[signupEntryIndex]
    
    def fillText(sorted_components,personInfo):
        model,infocols,infocols_embeddings,infoCSV=initSentenceTransformer()
        csvColumns=getSimilarColumn(sorted_components,infocols,infocols_embeddings,model)
        #If getSimilarColumn() fails due to empty labels
        if not csvColumns:
            #Separate the edittext components
            editTexts=[]
            for comp in sorted_components:
                if "edittext" in comp.component_class.lower():
                    editTexts.append(comp)
        #print("sorted components length: ",len(sorted_components))
        for i,component in enumerate(sorted_components):
            print("working with ="+component.resource_id+", "+component.component_class+", "+component.text.lower())
            if "edittext" in component.component_class.lower():
                print("Got an edit text.",end="\t")
                print(component.resource_id)
                print("Going to choose from:",end=" ")
                print(csvColumns)
                col=csvColumns[i]
                inputText=str(personInfo[col])
                interactions.textField(dc,device,component,inputText,logFile)
            #Spinner heuristic, other heuristics can also be added later
            elif "spinner" in component.component_class.lower():
                #print("Got a spinner.")
                interactions.spinner(dc,device,component,logFile)
                
    
     
    #Get screen dimensions
    width=device.screen_width
    height=device.screen_height

    #Get sentence transformer model and embeddings for the csv columns
    model,infocols,infocols_embeddings,info=initSentenceTransformer()
    #Seperating login buttons and signup buttons
    loginButtons=["log in","sign in", "login"]
    signupButtons=["sign up", "create account"]
    #See if AURORA can login to this app
    doLogin,loginEntryIndex=canLogin(dc,device,info)
    #Get login/signup info from info.csv
    personInfo=getPersonInfo(dc,device,info,doLogin,loginEntryIndex)
    

    
    # If Aurora does not provide any components, then get them here using getClickables() and sort them
    if len(clickable_components)<1:
        clickable_components=dp.getClickables(dc,device)
        
    sorted_components,buttons,edittexts=dp.sortComponents(clickable_components)
    
    
    # If there are more than or less than 2 edittexts
    #then we cannot just enter email and password
    #we need to find the login button and get to the 2-edittext screen
    if len(edittexts)!=2:
        loginButton=getPressButtonLikeComponent(buttons,loginButtons,model)
        dc.send_event(device,atl.Tap(*loginButton.center))
        #Wait upto 5 seconds
        for i in range(5):
            sorted_components,buttons,edittexts=refreshComponents(dc,device)
            if len(edittexts)>0: break
            else: time.sleep(1)
        sorted_components,buttons,edittexts=refreshComponents(dc,device)
        fillText(sorted_components,personInfo)
        loginButton=getPressButtonLikeComponent(buttons,loginButtons,model)
        print("Printing the login button that we found:",end=" ")
        print(loginButton)
        print("Login button bounds: ",loginButton.bounds)
        #dc.send_event(device,atl.Tap(*loginButton.center))
        act,cc=interactions.pressButton(dc,device,clickable_components,loginButton,logFile)
        #return
            
    else:
        sorted_components,buttons,edittexts=refreshComponents(dc,device)
        fillText(sorted_components,personInfo)
        loginButton=getPressButtonLikeComponent(buttons,loginButtons,model)
        #dc.send_event(device,atl.Tap(*loginButton.center))
        act,cc=interactions.pressButton(dc,device,clickable_components,loginButton,logFile)
        #return
        
    #We wait for upto 5 seconds incrementally and check if activity has changed
    for i in range(5):
        act=dc.get_current_activity(device)
        if act!=actExplored[-1]:
            break
        else:
            time.sleep(1)
    if act not in actExplored: actExplored.append(act)
    if cc: ccChanged+=1
    act=dc.get_current_activity(device)
    actChange=len(actExplored)-1
    
    return actChange,ccChanged
            
            


# In[ ]:


# dc = atl.DeviceConnector()
# device_list = dc.enumerate_discoverable_devices()

# device = dc.get_device(name = device_list[0].name, sdk_level=device_list[0].sdk_level)
# screen_width=device.screen_width
# screen_height=device.screen_height
# resolution=(screen_width,screen_height)
# resized_resolution=(144,256)
# clickable_components=dp.getClickables(dc,device)


# In[ ]:


# loginHeuristics(dc,device,clickable_components)


# In[ ]:


# dc.get_current_activity(device)


# In[ ]:





# In[ ]:





#!/usr/bin/env python
# coding: utf-8

# In[1]:


import torch
import torch.nn as nn
import torch.nn.functional as F
from Saved_Models.model import *
from Saved_Models.utils import *
import cv2
import DataPreparation as dp


# In[ ]:


#Changed probaLog() output
#since our new classifier provides us the prediction labels
# as opposed to the probability matrix of our previous classifier
def probaLog(combinedProba):
    import json
    # Opening JSON file
    with open('labelMapping.json') as json_file:
        labelMapping = json.load(json_file)
    output=""
    for i,p in enumerate(combinedProba):
        output+=str(i+1)+": "+labelMapping[str(p)]+"\n"
    return output


# In[4]:


def initClassifierModel(modelfilename):
    model = RICOScreenClassifer(21, device="cuda")
    if modelfilename != '':
        checkpoint = torch.load(modelfilename,map_location=torch.device('cpu'))
        model_dict = model.state_dict()
        model_dict.update(checkpoint)
        model.load_state_dict(model_dict)
    model = model.cuda()
    model.eval()
    return model


# In[ ]:


def classifyScreen(ss,sil,ocr,model,logPath):
    ss=cv2.imread(ss,1)
    ss_preproc = encoder_image_preprocess(ss, 224, 224)
    sil_preproc = encoder_image_preprocess(sil, 224, 224)
    
    ss_inputs = torch.from_numpy(ss_preproc)
    sil_inputs = torch.from_numpy(sil_preproc)
    
    ss_inputs = ss_inputs.unsqueeze(0).cuda()
    sil_inputs = sil_inputs.unsqueeze(0).cuda()
    
    texts = [ocr]
    
    outputs = model(ss_inputs, sil_inputs, texts)
    
    preds = F.softmax(outputs, dim=1)
    sortedPreds=preds[0].sort(descending=True,stable=True)
    allPreds=sortedPreds.indices[:].tolist()
    
    probabilities=probaLog(allPreds)
    dp.updateLog(logPath,probabilities,"classifier")
    topPreds=sortedPreds.indices[:3].tolist()
    return topPreds


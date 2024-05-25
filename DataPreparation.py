#!/usr/bin/env python
# coding: utf-8

# In[ ]:


from PIL import Image, ImageDraw
import pandas as pd
import AndroidTestingLibraryLocal as atl
import time
import json
import os
from os.path import join as pjoin
from PIL import Image, ImageDraw
import cv2
import regex as re
import numpy as np


# In[ ]:


# !pip install uiautomator


# In[ ]:


resized_resolution=(144,256)


# In[ ]:


def getScreenshot(dc,device,ssPath):
    dc.get_screen_capture(device,ssPath)
    ss=cv2.imread(ssPath, 1)
    return ss


# In[ ]:


def getClickablesXML(filename,destPath):
    from ppadb.client import Client as AdbClient
    from AndroidTestingLibraryLocal import GuiComponent
    client = AdbClient(host="127.0.0.1", port=5037)
    ppadb_device = client.device("emulator-5554")
    ppadb_device.shell("uiautomator dump")
    ppadb_device.pull("/sdcard/"+filename, destPath)
    import xml.etree.ElementTree as ET
    tree = ET.parse(destPath)
    root = tree.getroot()
    clickable_components=[]
    guicomp=GuiComponent.make_gui_component(root[len(root)-1], None)
        # iterate through the components and look for matches with search parameters
    for component in reversed(guicomp.iterate_hierarchy()):
        if component.resource_id:
            clickable_components.append(component)
    return clickable_components


# In[ ]:


#Compares to clickableComponents lists
#Returns True if cc2 is different from cc1
def differentClickables(cc1,cc2):
    l1=len(cc1)
    l2=len(cc2)
    def clickableInfo(cc):
        try:
            return cc.component_class+" "+cc.resource_id
        except:
            return cc.component_class
    compFound=False
    if l1!=l2:
        return True
    else:
        for c1 in cc1:
            for c2 in cc2:
                if clickableInfo(c1)==clickableInfo(c2):
                    compFound=True
                    break
            if not compFound:
                return True
                    
    return False
    


# In[ ]:


def getFilePaths(appPackage,trace):
    import time
    parentFolder="Runtime_Files"
    
    os.makedirs(pjoin(parentFolder,appPackage+"-"+trace),exist_ok=True)
    e=time.time()
    curDateTime=str(int(e))
    
    filename=appPackage+"_"+curDateTime+".jpg"
    ssPath=pjoin(parentFolder,appPackage+"-"+trace,filename)
    hierPath=pjoin(parentFolder,appPackage+"-"+trace,filename.replace(".jpg",".xml"))
    silPath=pjoin(parentFolder,appPackage+"-"+trace,filename.replace(".jpg",".sil.png"))
    logPath=pjoin(parentFolder,appPackage+"-"+trace,filename.replace(".jpg",".log"))
    ocrPath=logPath.replace(".log",".ocr.txt")
    return silPath,ssPath,hierPath,ocrPath,logPath,curDateTime


# In[ ]:


# Connecting to the virtual device using Android Testing Library
def getDeviceInfo(): 
    dc = atl.DeviceConnector()
    device_list = dc.enumerate_discoverable_devices()

    device = dc.get_device(name = device_list[0].name, sdk_level=device_list[0].sdk_level)
    resolution=(device.screen_width,device.screen_height)
    return dc,device,resolution


# In[ ]:


def updateLog(logfilepath,log="",mode=""):
    startTimeStamp=int(logfilepath.split("_")[-1].split(".")[0])
    import time
    e=time.time()
    curTimeStamp=int(time.time())
    timestampText="[at "+str(curTimeStamp-startTimeStamp)+" second] "
    if len(mode)>0:
        mode="-"+mode.upper()
    if not os.path.exists(logfilepath):
        with open(logfilepath, 'w') as logfile: 
            if log:
                logfile.write("[AURORA"+mode+"] "+timestampText+log+"\n")
    else:
        with open(logfilepath,'a') as logfile:
            if log:
                logfile.write("[AURORA"+mode+"] "+timestampText+log+"\n")


# In[ ]:


def getComponentInfo(actionText,component=None):
    outputText=actionText
    try:
        resID=component.resource_id
        outputText+="comp_id: "+resID+", "
        outputText+="comp_class: "+component.component_class+", "
        outputText+="comp_bounds: "+str(component.bounds)
    except:
        outputText="NoneType object"
    return outputText


# In[ ]:


def getRelevantComponents(clickable_components,relComponents):
    for comp in clickable_components:
        if len(comp.children)>0:
            for child in comp.children:
                getRelevantComponents(child,relComponents)
        else:
            if not "layout" in comp.component_class.lower():
                if comp not in relComponents:
                    relComponents.append(comp)


# In[ ]:


def getClickables(dc,device,dumpFile=""):
    import os
    from os.path import join as pjoin
    import datetime
    import xml.etree.ElementTree as ET
    from AndroidTestingLibraryLocal import GuiComponent
    screen_width=device.screen_width
    screen_height=device.screen_height
    clickable_components=dc.search_gui_components(device, event_type = atl.Tap)
    if len(clickable_components)==0:
        #print("No components found using atl, going to use uiautomator API.")
        from uiautomator import device as d
        from uiautomator import Device
        d=Device(dc.get_device().serial)
        #If dumpFile name is specified, dump as that filename and path
        #Else save a temp.xml file
        dumpFile=dumpFile if len(dumpFile)>0 else "temp.xml"
        
        
        xml=d.dump(dumpFile)
        tree = ET.ElementTree(ET.fromstring(xml))
        root = tree.getroot()
        lenXML=len(root)
        #If the XML has no hierarchies
        # wake-swipe the device and then try dumping xml again
        if lenXML==0:
            wakeActions=[atl.Swipe(int(device.screen_width/2), 10, 0, 10, 1),
                            atl.Tap(int(device.screen_width/2),int(device.screen_height/2)),
                         atl.BackButton()]
            for action in wakeActions:
                dc.send_event(device, action)
                xml=d.dump(dumpFile)
                tree = ET.ElementTree(ET.fromstring(xml))
                root = tree.getroot()
                time.sleep(1)
                lenXML=len(root)
                if lenXML>0: break
            
        guicomp=GuiComponent.make_gui_component(root[len(root)-1], None)
        # iterate through the components and look for matches with search parameters
        for component in reversed(guicomp.iterate_hierarchy()):
            if component.resource_id:
                clickable_components.append(component)
    else:
        
        xml=dc.get_gui_hier(device)
        if len(dumpFile)>0:
            hier_file = open(dumpFile, "wt",encoding="utf-8")
            hier = hier_file.write(xml)
            hier_file.close()
    #print("UIAutomator API found ",len(clickable_components)," components.")
    relComponents=[]
    getRelevantComponents(clickable_components,relComponents)
    return relComponents


# In[ ]:


# def getClickables(dc,device,dumpFile=""):
#     import os
#     from os.path import join as pjoin
#     import datetime
#     import xml.etree.ElementTree as ET
#     from AndroidTestingLibraryLocal import GuiComponent
#     screen_width=device.screen_width
    
#     clickable_components=dc.search_gui_components(device, event_type = atl.Tap)
#     if len(clickable_components)==0:
#         #print("No components found using atl, going to use uiautomator API.")
#         from uiautomator import device as d
#         from uiautomator import Device
#         d=Device(dc.get_device().serial)
#         #If dumpFile name is specified, dump as that filename and path
#         #Else save a temp.xml file
#         dumpFile=dumpFile if len(dumpFile)>0 else "temp.xml"
        
        
#         xml=d.dump(dumpFile)
#         tree = ET.ElementTree(ET.fromstring(xml))
#         root = tree.getroot()
#         lenXML=len(root)
#         #If the XML has no hierarchies
#         # wake-swipe the device and then try dumping xml again
#         if lenXML==0:
#             while lenXML==0:
#                 dc.send_event(device, atl.Swipe(int(screen_width/2), 0, 0, 0, 1))
#                 xml=d.dump(dumpFile)
#                 tree = ET.ElementTree(ET.fromstring(xml))
#                 root = tree.getroot()
#                 lenXML=len(root)
            
#         guicomp=GuiComponent.make_gui_component(root[len(root)-1], None)
#         # iterate through the components and look for matches with search parameters
#         for component in reversed(guicomp.iterate_hierarchy()):
#             if component.resource_id:
#                 clickable_components.append(component)
#     else:
        
#         xml=dc.get_gui_hier(device)
#         if len(dumpFile)>0:
#             hier_file = open(dumpFile, "wt",encoding="utf-8")
#             hier = hier_file.write(xml)
#             hier_file.close()
#     #print("UIAutomator API found ",len(clickable_components)," components.")
#     relComponents=[]
#     getRelevantComponents(clickable_components,relComponents)
#     return relComponents


# In[ ]:


class interactions:
    
    def textField(dc,device,component, text,logFile,delExisting=True):
        dc.send_event(device,atl.Tap(*component.right))
        if delExisting:
            #Delete existing text
            dc.send_event(device,atl.MoveEnd())
            dc.send_event(device,atl.LongBackSpace())
        #Enter text
        dc.send_event(device,atl.Text(text))
        #dc.send_event(device,atl.BackButton())
        print("Heuristics entered text.")
        logText=getComponentInfo("Entered "+text+" on ",component)
        updateLog(logFile,logText,"heuristics")
        time.sleep(500/1000)
    
    def textFieldNoComp(dc,device,x,y,text,logFile,delExisting=True):
        dc.send_event(device,atl.Tap(x,y))
        if delExisting:
            #Delete existing text
            dc.send_event(device,atl.MoveEnd())
            dc.send_event(device,atl.LongBackSpace())
        #Enter text
        dc.send_event(device,atl.Text(text))
        #dc.send_event(device,atl.BackButton())
        print("Heuristics entered text.")
        logText="Entered "+text
        updateLog(logFile,logText,"heuristics")
        time.sleep(500/1000)
    
    def pressButton(dc,device,prev_clickables,component,logFile):
        try:
            resID=component.resource_id
        except:
            resID=""
        prevActivity=dc.get_current_activity(device)
        print("Activity before pressButton(): ",prevActivity)
        time.sleep(500/1000)
        dc.send_event(device,atl.Tap(*component.center))
        print("Heuristics pressed button "+resID+".")
#         sleepTime=0
#         while(sleepTime<5):
            
#             if curActivity!=prevActivity:
#                 break
#             time.sleep(1)
#             sleepTime+=1
        curActivity=dc.get_current_activity(device)
        print("Activity after pressButton(): ",curActivity)
        logText1=getComponentInfo("Tapped on button: ",component)
        logText2="Prev activity: "+str(prevActivity)+", Curr activity: "+str(curActivity)
        updateLog(logFile,str(logText1)+str(logText2),"heuristics")
        if curActivity!=prevActivity:
            print("Navigated from activity:"+str(prevActivity)+" to activity:"+str(curActivity))
        
        cur_clickables=getClickables(dc,device,dumpFile="")
        ccChange=differentClickables(prev_clickables,cur_clickables)
        return curActivity,ccChange
       
    def pressButtonNoComp(dc,device,prev_clickables,x,y,logFile):
        resID=""
        prevActivity=dc.get_current_activity(device)
        print("Activity before pressButton(): ",prevActivity)
        time.sleep(500/1000)
        dc.send_event(device,atl.Tap(x,y))
        print("Heuristics pressed on",end=": ")
        print(x,y)
        curActivity=dc.get_current_activity(device)
        print("Activity after pressButton(): ",curActivity)
        logText1="Tapped on coordinate: "+str(x)+", "+str(y)
        logText2="Prev activity: "+str(prevActivity)+", Curr activity: "+str(curActivity)
        updateLog(logFile,str(logText1)+str(logText2),"heuristics")
        if curActivity!=prevActivity:
            print("Navigated from activity:"+str(prevActivity)+" to activity:"+str(curActivity))
        
        cur_clickables=getClickables(dc,device,dumpFile="")
        ccChange=differentClickables(prev_clickables,cur_clickables)
        return curActivity,ccChange
    
    def spinner(dc,device,component,logFile):
        import random
        dc.send_event(device,atl.Tap(*component.center))
        time.sleep(100/1000)
        clickable_components=dc.search_gui_components(device, event_type = atl.Tap)
        time.sleep(100/1000)
        randomEntry=random.randint(1,(len(clickable_components)-1))
        dc.send_event(device,atl.Tap(*clickable_components[randomEntry].center))
        time.sleep(100/1000)
        logText=getComponentInfo("Changed spinner: ",component)
        updateLog(logFile,logText,"heuristics")
        print("Heuristics changed spinner.")
    
#     def searchString(dc,device,prev_clickables,component,logFile,text=""):
#         import random
#         import string
#         prevActivity=dc.get_current_activity(device)
#         print("Activity before pressButton(): ",prevActivity)
#         text= random.choice(string.ascii_letters) if len(text)<1 else text
#         #Delete existing text
#         dc.send_event(device,atl.MoveEnd())
#         dc.send_event(device,atl.LongBackSpace())
#         #Enter text
#         dc.send_event(device, atl.Text(text))
#         #After typing a random letter, press downkey and then enter
#         dc.send_event(device,atl.DownKey())
#         dc.send_event(device,atl.EnterKey())
#         time.sleep(1)
#         curActivity=dc.get_current_activity(device)
#         try:
#             logText=getComponentInfo("Entered random letter on search field and picked the first result: ",component)
#         except:
#             logText=getComponentInfo("Entered random letter on search field and picked the first result: ")
#         updateLog(logFile,logText,"heuristics")
#         print("Heuristics searched and picked from search field.")
        
#         cur_clickables=getClickables(dc,device,dumpFile="")
#         ccChange=differentClickables(prev_clickables,cur_clickables)
#         return curActivity,ccChange
    def searchString(dc,device,prev_clickables,component,logFile,text=""):
        import random
        import string
        prevActivity=dc.get_current_activity(device)
        print("Activity before pressButton(): ",prevActivity)
        text= random.choice(string.ascii_letters) if len(text)<1 else text
        #Delete existing text
        dc.send_event(device,atl.MoveEnd())
        dc.send_event(device,atl.LongBackSpace())
        #Enter text
        dc.send_event(device, atl.Text(text))
        
        curActivity=dc.get_current_activity(device)
        
        logText=getComponentInfo("Entered search string on search field.")
        updateLog(logFile,logText,"heuristics")
        print("Heuristics searched for a string.")
        
        cur_clickables=getClickables(dc,device,dumpFile="")
        ccChange=differentClickables(prev_clickables,cur_clickables)
        return curActivity,ccChange
    
    
    def swipe(dc,device,prev_clickables,direction,logFile):
        dx,dy=0,0
        if direction=="left":
            dx=-500
        elif direction=="right":
            dx=500
        elif direction=="up":
            dy=-500
        elif direction=="down":
            dy=500
        prevActivity=dc.get_current_activity(device)
        print("Activity before swipe(): ",prevActivity)
        time.sleep(500/1000)
        dc.send_event(device, atl.Swipe(int(device.screen_width/2),int(device.screen_height/2),dx,dy,100))
        print("Heuristics swiped screen "+direction+".")
        #time.sleep(5)
        curActivity=dc.get_current_activity(device)
        print("Activity after swipe(): ",curActivity)
        logText1="Swiped "+direction+"."
        logText2="Prev activity: "+str(prevActivity)+", Curr activity: "+str(curActivity)
        updateLog(logFile,logText1+logText2,"heuristics")
        if curActivity!=prevActivity:
            print("Navigated from activity:"+str(prevActivity)+" to activity:"+str(curActivity))
        cur_clickables=getClickables(dc,device,dumpFile="")
        ccChange=differentClickables(prev_clickables,cur_clickables)
        return curActivity,ccChange
        


# In[ ]:





# In[ ]:


def getRootComponent(dc,device):
    root_component = None
    while root_component is None:
        root_component = dc.get_gui(device)
    return root_component


# In[ ]:


def getData(data,attribute):
    blank=""
    if(data.get(attribute)):
        return data.get(attribute)
    else:
        return blank


# In[ ]:


def sort_horizontally(tup):
    #Sorting by averaging the y-axis values of the component's bounds
#     tup.sort(key = lambda c: (c.bounds[0][1]+c.bounds[1][1])/2)
    #Sorting by the top y-axis value of the component's bounds
    tup.sort(key = lambda c: c.bounds[0][1])
    return tup


# In[ ]:


#Checks for clickable components and
#returns two lists: edittexts and buttons
def sortComponents(clickable_components):
    #clickable_components=dc.search_gui_components(device, event_type = atl.Tap)
    edittexts=[]
    buttons=[]
    for c in clickable_components:
        if "edittext" in c.component_class.lower():
            edittexts.append(c)
        elif "button" in c.component_class.lower():
            buttons.append(c)
    #If there are no button components,
    #Then add the clickable textview components in buttons
    if len(buttons)==0:
        for c in clickable_components:
            if "textview" in c.component_class.lower():
                buttons.append(c)
    buttons=sort_horizontally(buttons)
    edittexts=sort_horizontally(edittexts)
    sorted_components=sort_horizontally(clickable_components)
    return sorted_components,buttons,edittexts


# In[ ]:


def getLeafComponents(root_component,componentList):
    if root_component.children:
        componentList.append(root_component)
    else:
        for child in root_component.children:
            getLeafComponents(child,componentList)


# In[ ]:


# def createSilhouette(componentList,resolution,csvFile,save_as):
#     width,height=resolution
#     def getLabelColor(csvFile):
#         df=pd.read_csv(csvFile)
#         labelColor={}
#         for i in range(len(df)):
#             l,c=df.loc[i]
#             labelColor[l]=c
#         return labelColor
#     labelColorObj=getLabelColor(csvFile)
#     img = Image.new("RGB", (width, height))
#     for comp in componentList:
#         bound=comp.bounds
#         for obj in labelColorObj:
#             if obj.lower() in comp.component_class.lower():
#                 shape=list(bound)
#                 drawObj=ImageDraw.Draw(img)
#                 drawObj.rectangle(shape,fill=labelColorObj[obj],outline=labelColorObj[obj],width=10)
#     img=img.resize(resized_resolution)
#     img.save(save_as)
#     return img


# In[ ]:


def getHW(bounds,resolution,height=0,width=0):
    #In case we pass bounds like this: ((x1,y1),(x2,y2))
    if len(bounds)==2:
        bounds=[bounds[0][0],bounds[0][1],bounds[1][0],bounds[1][1]]
    if height==0 and width==0:
        try:
            heightNum=abs(bounds[1]-bounds[3])
        except:
            heightNum=0
        try:
            widthNum=abs(bounds[0]-bounds[2])
        except:
            widthNum=0
    else:
        heightNum=height
        widthNum=width
    if(heightNum<(0.25*resolution[1])):
        height="low-height"
    elif (heightNum<(0.5*resolution[1])):
        height="medium-height"
    else:
        height="high-height"
    
    if(widthNum<(0.25*resolution[0])):
        width="low-width"
    elif (widthNum<(0.5*resolution[0])):
        width="medium-width"
    else:
        width="high-width"
    return height,width
    
def getPosition(bounds,resolution):
    #In case we pass bounds like this: ((x1,y1),(x2,y2))
    if len(bounds)==2:
        bounds=[bounds[0][0],bounds[0][1],bounds[1][0],bounds[1][1]]

    try:
        bMidXPerc=((bounds[0]+bounds[2])/2)/resolution[0]*100
    except:
        bMidXPerc=0
    try:
        bMidYPerc=((bounds[1]+bounds[3])/2)/resolution[0]*100
    except:
        bMidYPerc=0
    if bMidXPerc<25:
        if bMidYPerc<25:
            return "top-left"
        elif bMidYPerc>=75:
            return "bottom-left"
        else:
            return "center-left"
    elif bMidXPerc>=75:
        if bMidYPerc<25:
            return "top-right"
        elif bMidYPerc>=75:
            return "bottom-right"
        else:
            return "center-right"
    else :
        if bMidYPerc<25:
            return "top-center"
        elif bMidYPerc>=75:
            return "bottom-center"
        else :
            return "center"


# In[ ]:


# Get text json object and text
# Using UIED ocr detection
import UIED_detect_text.ocr as ocr
from UIED_detect_text.Text import Text
from UIED_detect_text.text_detection import text_cvt_orc_format
from UIED_detect_text.text_detection import merge_intersected_texts
from UIED_detect_text.text_detection import text_filter_noise
from UIED_detect_text.text_detection import text_sentences_recognition
def getTextJson(input_img):
    def get_detection_jsonObj(texts, img_shape):
        output = {'img_shape': img_shape, 'texts': []}
        for text in texts:
            c = {'id': text.id, 'content': text.content}
            loc = text.location
            c['column_min'], c['row_min'], c['column_max'], c['row_max'] = loc['left'], loc['top'], loc['right'], loc['bottom']
            c['width'] = text.width
            c['height'] = text.height
            output['texts'].append(c)
        #json.dump(output, f_out, indent=4)
        return output
    img = cv2.imread(input_img)
    ocr_result = ocr.ocr_detection_google(input_img)
    texts = text_cvt_orc_format(ocr_result)
    texts = merge_intersected_texts(texts)
    texts = text_filter_noise(texts)
    texts = text_sentences_recognition(texts)
    newJson=get_detection_jsonObj(texts, img.shape)
    
    
    resolution=[newJson.get("img_shape")[1],newJson.get("img_shape")[0]]
    outputText="[SEP]".join([text.get("content") for text in newJson.get("texts")])
    outputText=outputText.strip()
    outputText=re.sub(' +', ' ', outputText)
    outputText=outputText.replace(",","")
    
    #open text file
    output_file=input_img.replace(".jpg",".ocr.txt")
    text_file = open(output_file, "w",encoding="utf-8") 
    #write string to file
    text_file.write(outputText)
    #close file
    text_file.close()
    return newJson,outputText


# In[ ]:


#Get Component info from screenshot
#Using UIED
#Component detection imports
import UIED_detect_compo.lib_ip.ip_preprocessing as pre
import UIED_detect_compo.lib_ip.ip_draw as draw
import UIED_detect_compo.lib_ip.ip_detection as det
import UIED_detect_compo.lib_ip.file_utils as file
import UIED_detect_compo.lib_ip.Component as Compo
from PIL import Image, ImageDraw
#Get component json object

def getCompJson(input_img_path, resize_by_height=800, classifier=None, show=False, wai_key=0):
    #resize_by_height is set to 800 to get rid of unwanted granularity within components
    import time
    uied_params = {'min-grad':10, 'ffl-block':5, 'min-ele-area':50,
              'merge-contained-ele':True, 'merge-line-to-paragraph':False, 'remove-bar':True}
    def get_corners_json(compos):
        img_shape = compos[0].image_shape
        output = {'img_shape': img_shape, 'compos': []}

        for compo in compos:
            c = {'id': compo.id, 'class': compo.category}
            (c['column_min'], c['row_min'], c['column_max'], c['row_max']) = compo.put_bbox()
            c['width'] = compo.width
            c['height'] = compo.height
            output['compos'].append(c)
        return output
    def nesting_inspection(org, grey, compos, ffl_block):
        '''
        Inspect all big compos through block division by flood-fill
        :param ffl_block: gradient threshold for flood-fill
        :return: nesting compos
        '''
        nesting_compos = []
        for i, compo in enumerate(compos):
            if compo.height > 50:
                replace = False
                clip_grey = compo.compo_clipping(grey)
                n_compos = det.nested_components_detection(clip_grey, org, grad_thresh=ffl_block, show=False)
                Compo.cvt_compos_relative_pos(n_compos, compo.bbox.col_min, compo.bbox.row_min)

                for n_compo in n_compos:
                    if n_compo.redundant:
                        compos[i] = n_compo
                        replace = True
                        break
                if not replace:
                    nesting_compos += n_compos
        return nesting_compos

    start = time.time()
    name = input_img_path.split('/')[-1][:-4] if '/' in input_img_path else input_img_path.split('\\')[-1][:-4]
    #print(input_img_path)
    # *** Step 1 *** pre-processing: read img -> get binary map
    org, grey = pre.read_img(input_img_path, resize_by_height)
    binary = pre.binarization(org, grad_min=int(uied_params['min-grad']))

    # *** Step 2 *** element detection
    det.rm_line(binary, show=show, wait_key=wai_key)
    uicompos = det.component_detection(binary, min_obj_area=int(uied_params['min-ele-area']))

    # *** Step 3 *** results refinement
    uicompos = det.compo_filter(uicompos, min_area=int(uied_params['min-ele-area']), img_shape=binary.shape)
    uicompos = det.merge_intersected_compos(uicompos)
    det.compo_block_recognition(binary, uicompos)
    if uied_params['merge-contained-ele']:
        uicompos = det.rm_contained_compos_not_in_block(uicompos)
    Compo.compos_update(uicompos, org.shape)
    Compo.compos_containment(uicompos)

    Compo.compos_update(uicompos, org.shape)
    compJson=get_corners_json(uicompos)
    #print("[Compo Detection Completed in %.3f s] Input: %s Output: %s" % (time.time() - start, input_img_path, pjoin(ip_root, name + '.json')))
    return compJson


# In[ ]:


#Merging text_json and component_json that we get from UIED
#to create final json that consists of both textual and non-textual objects
def merge(img, compo_json, text_json, merge_root=None, is_paragraph=False, is_remove_bar=True, show=False, wait_key=0):
    from UIED_detect_merge.Element import Element
    from UIED_detect_merge import merge

    def get_elements(elements, img_shape):
        components = {'compos': [], 'img_shape': img_shape}
        for i, ele in enumerate(elements):
            c = ele.wrap_info()
            # c['id'] = i
            components['compos'].append(c)
        #json.dump(components, open(output_file, 'w'), indent=4)
        return components


    # load text and non-text compo
    ele_id = 0
    compos = []
    for compo in compo_json['compos']:
        element = Element(ele_id, (compo['column_min'], compo['row_min'], compo['column_max'], compo['row_max']), compo['class'])
        compos.append(element)
        ele_id += 1
    texts = []
    for text in text_json['texts']:
        element = Element(ele_id, (text['column_min'], text['row_min'], text['column_max'], text['row_max']), 'Text', text_content=text['content'])
        texts.append(element)
        ele_id += 1
    if compo_json['img_shape'] != text_json['img_shape']:
        resize_ratio = compo_json['img_shape'][0] / text_json['img_shape'][0]
        for text in texts:
            text.resize(resize_ratio)

    # check the original detected elements
    #print(img_path)
    #img = cv2.imread(img_path)
    #print(compo_json['img_shape'])
    img_resize = cv2.resize(img, (compo_json['img_shape'][1], compo_json['img_shape'][0]))
    #merge.show_elements(img_resize, texts + compos, show=show, win_name='all elements before merging', wait_key=wait_key)

    # refine elements
    texts = merge.refine_texts(texts, compo_json['img_shape'])
    elements = merge.refine_elements(compos, texts)
    if is_remove_bar:
        elements = merge.remove_top_bar(elements, img_height=compo_json['img_shape'][0])
        elements = merge.remove_bottom_bar(elements, img_height=compo_json['img_shape'][0])
    if is_paragraph:
        elements = merge.merge_text_line_to_paragraph(elements, max_line_gap=7)
    merge.reassign_ids(elements)
    merge.check_containment(elements)
    #board = merge.show_elements(img_resize, elements, show=show, win_name='elements after merging', wait_key=wait_key)

    # save all merged elements, clips and blank background
    #name = img_path.replace('\\', '/').split('/')[-1][:-4]
    components = get_elements(elements, img_resize.shape)
    #cv2.imwrite(pjoin(merge_root, name + '.jpg'), board)
    #print('[Merge Completed] Input: %s Output: %s' % (img_path, pjoin(merge_root, name + '.jpg')))
    return components


# In[1]:


def createOCR_text_layout(fileDir,resolution,constraints=0):
    fileName=fileDir.split("\\")[-1]
    compJson=getCompJson(fileDir)
    textJson,ocrText=getTextJson(fileDir)
    img=cv2.imread(fileDir)
    merged_comp=merge(img,compJson,textJson)
    #print(fileDir)
    tShapes=[]
    ntShapes=[]
    ocr_resolution=tuple(reversed(merged_comp.get("img_shape")[:-1]))
    multiplier=[size/ocr_resolution[i] for i,size in enumerate(resolution)]

    for compos in merged_comp.get("compos"):
        compText=compos.get("text_content")
        position=compos.get("position")
        x1,y1,x2,y2=position.get("column_min"),position.get("row_min"),position.get("column_max"),position.get("row_max")
        x1*=multiplier[0]
        y1*=multiplier[1]
        x2*=multiplier[0]
        y2*=multiplier[1]
        if compos.get("class")=="Compo":
            if constraints!=0:
                width=abs(x2-x1)
                height=abs(y2-y1)
                area=width*height
                if width<constraints[0] and height<constraints[1] and area<constraints[2]:
                    ntShapes.append([compText,[(x1,y1),(x2,y2)]])
            else:
                ntShapes.append([compText,[(x1,y1),(x2,y2)]])
        else:
            tShapes.append([compText,[(x1,y1),(x2,y2)]])

    # creating new Image object
    
    sil_img = Image.new("RGB", (resolution[0],resolution[1] ))
    # create rectangle images
    
    for _,shape in tShapes:
        textObj=ImageDraw.Draw(sil_img)
        #Text object will be drawn in blue
        textObj.rectangle(shape, fill ="#0000ff", outline ="blue",width=0)  
    for _,shape in ntShapes:
        #Non text object will be drawn in green
        nontextobj=ImageDraw.Draw(sil_img)
        nontextobj.rectangle(shape, fill ="#00ff00", outline ="green", width=0)
        
    sil_img.save(fileDir.replace(".jpg",".sil.png"))
    
    #Convert PIL image to cv2 format image
    sil_cv = np.array(sil_img) 
    # Convert RGB to BGR 
    sil_cv = sil_cv[:, :, ::-1].copy() 
    return ocrText,sil_cv,tShapes,ntShapes


# In[ ]:





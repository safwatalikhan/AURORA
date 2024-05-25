**Apps:** [**AURORA - Apps**](https://drive.google.com/file/d/13l3617yM8lMXpthNEZQFwWPoeiIi7C0A/view?usp=sharing)

Here we provide APK files for 17 android applications we used for our evaluation.  
This zip file should take up 873.7 MB when extracted.

**\***This zip file also includes the Null_Keyboard APK, which is used to ignore the android physical keyboard during the experimental runs.

&nbsp;**Labeled dataset:** [**AURORA - Labeled Dataset**](https://drive.google.com/file/d/1ZcFlw4Jh3WKYvpgWEnKeRUEENRf13P4Y/view?usp=sharing)

This zip file contains 21 subfolders where each of them represent a UI category and a total of **1369** labeled UI images and their supplementary information (UI metadata, OCR text, OCR json, and Screen Silhouette).

**Code:** [**AURORA**](https://drive.google.com/file/d/103_EBEbniyXPG64j-cs_oiL5rjCsATvr/view?usp=sharing)

Aurora is an automated input generation tool which uses computer vision and natural language processing techniques for navigating through a given screen. Running any well-known AIG tool such as Ape as a starting point, Aurora waits until it gets stuck on a screen. When it does, Aurora classifies the current screen into one of 21 UI labels (e.g. Login screen, Advertisement, Player screen etc.) using computer vision and NLP techniques, and then applies the suitable heuristics for navigating that screen.

Source code for our tool AURORA including a shell script (runAurora.sh) for running AURORA. The frozen classifier models (_rico_screen_classifier_extenddata_acc81.pth_ and _rico_screen_classifier_onlyrico_acc74.pth_) are located inside the "Saved_Models" folder.  
This zip file should amount to 1.9 GB when extracted.

**Setup and Run Instructions**

- Install Python 3.8.1 (<https://www.python.org/downloads/release/python-3810/>)
- Make sure pip is installed. You can enable pip installation during the Python installation wizard, or run the following command  
    python get-pip.py
- Make sure both pip and python directory are included in your System Path of your Environment Variable (Windows).
- Install the required packages listed here:
  - pandas pip install pandas
  - scikit-learn pip install scikit-learn
  - nltk pip install nltk
  - torch pip install torch==1.12.1
  - transformers pip install transformers==4.21.2
  - tensorflow pip install tensorflow==2.9.1
  - PIL pip install pillow
  - uiautomator pip install uiautomator
  - skimage pip install scikit-image
  - matplotlib pip install matplotlib
  - psutil pip install psutil
  - ppadb pip install pure-python-adb
  - cv2 pip install opencv-python
  - tqdm pip install tqdm
  - sentence transformers pip install sentence-transformers

**Preparing Aurora folder**

- Download [this repository.](https://drive.google.com/file/d/103_EBEbniyXPG64j-cs_oiL5rjCsATvr/view?usp=sharing)
- Download the [Saved_Models.zip](https://drive.google.com/file/d/1jyT3j5tWm_2MZIOqVkitaUOt3OAquIT5/view?usp=sharing) and paste the decompressed folder inside the project folder. Make sure there are no parent folders (e.g. Saved_Models/saved_models)
- Download [ape.zip](https://drive.google.com/file/d/12FzYK9-03TSKud0J7MUIuuVto8AL8zpR/view?usp=sharing) and put it into AURORA folder, make sure there are no parent folders (e.g. Ape/ape/)
- Download [UIED.zip](https://drive.google.com/file/d/1X8DefPUG99WOgTQjscygRzSFcKoCM4gg/view?usp=sharing) and put it into AURORA folder, make sure there are no parent folders (e.g. UIED/uied/)
- In UIED_detect_text/ocr.py line 28, insert your own google vision api key

**CSVs, JSONs and TXTs we use in this project**

- _labelcode.csv_ file has the mapping of UI labels to integer (e.g Login screen -> 7, Advertisement->0).
- _labelMapping.json_ is the json version of labelcode.
- _label-color.csv_ has the color codes for each UI class types, which we follow while creating silhouette files during runtime.
- _info.csv_ has the login inputs for login heuristics, such as, name, username, password etc.
- _searchStrings.csv_ has example search strings relating to Search heuristics
- _wiki125k-words.txt_ is a list of wikipedia words which we use as our vocabulary for sentence transformer. This helps us learn the context of UI components.

**Python files**

- Python files ending with a capital H (such as advertisementH.py, loginH.py) are heuristics for that particular UI label.
- DataPreparation.py creates necessary files and processes them for our purpose.
- ClassifyScreen.py classifies the current screen.
- Aurora.py is the main python file for the tool, which we run.

**Running Aurora**

- Create an android virtual device and open it.
- Install an app and open it.
- Run the following command  python Aurora.py or open the notebook file Aurora.ipynb in Jupyter Notebook, then Cell-> Run all
- Aurora will start Ape at the beginning and monitor if it gets stuck for more than 10 seconds on a single activity. If it does, then our Classifier based Heuristic approach takes over. Once the heuristics actions have finished executing, Ape will resume.
- Aurora will store runtime images in the Runtime_Images directory. It has two subdirectories: Screenshots and Silhouettes

**Open source projects used**

1. [Ape](http://gutianxiao.com/ape/)
2. [UIED](https://github.com/MulongXie/UIED)
3. [UIAutomator](https://github.com/xiaocong/uiautomator)

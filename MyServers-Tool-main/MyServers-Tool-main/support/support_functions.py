import json
import os, secrets, base64
from datetime import datetime
from pathlib import Path
from support.support_variables import *
#from colorama import init, Fore, Style
from termcolor import colored, cprint




JsonDataPath = Path(__file__).with_name("data.json")


class MainFileIO:
    def __init__(self) -> None:
        pass
    
    def save_user_data(self, section, name, payload) -> None:
        if not name:
            DebugPrint("Name not initialized", "FileIO.save_user_data", warn=True)
            return
        
        if JsonDataPath.exists():
            try:
                write_data_bucket = json.loads(JsonDataPath.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                write_data_bucket = {}
        else:
            write_data_bucket = {}
        
        write_section_bucket = write_data_bucket.setdefault(section, {})
        write_section_bucket[name] = payload
        JsonDataPath.write_text(json.dumps(write_data_bucket, indent=2), encoding="utf-8")
    
    def retrieve_user_data(self, section=None, name=None, all=False):
        if JsonDataPath.exists():
            try:
                read_data_bucket = json.loads(JsonDataPath.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                read_data_bucket = {}
                DebugPrint(
                    "data.json is corrupted or invalid",
                    "FileIO.retrieve_user_data",
                    alert=True,
                )
                return {}
        else:
            read_data_bucket = {}
            DebugPrint("data.json does not exist", "FileIO.retrieve_user_data", warn=True)
        
        read_section_bucket = read_data_bucket.get(section, {})
        read_name_bucket = read_section_bucket.get(name, {})
        if name and section and not all:
            #DebugPrint(
            #    "Retrieved Requested Data [By name & section] From data.json",
            #    "FileIO.retrieve_user_data",
            #    multi=[read_name_bucket],
            #)
            return read_name_bucket
        if not name and section and not all:
            #DebugPrint(
            #    "Retrieved Requested Data [By section] From data.json", "FileIO.retrieve_user_data", multi=list(read_section_bucket.keys()) )
            return list(read_section_bucket.keys())
        if not name and not section and not all:
            #DebugPrint(
            #    "Retrieved All Data From data.json",
            #    "FileIO.retrieve_user_data",
            #    multi=[list(read_data_bucket.keys())],
            #)
            return list(read_data_bucket.keys())
        if all:
            #DebugPrint(
            #    "Retrieved All Data From data.json",
            #    "FileIO.retrieve_user_data",
            #    multi=[read_data_bucket],
            #)
            return read_data_bucket
        DebugPrint(
            "No valid parameters provided to retrieve data",
            "FileIO.retrieve_user_data",
            warn=True,
        )
        return None
    
    def delete_user_data(self, section, name) -> None:
        read_data_bucket = self.retrieve_user_data(all=True)
        read_section_bucket = read_data_bucket.setdefault(section, {})
        read_section_bucket.pop(name, None)
        JsonDataPath.write_text(json.dumps(read_data_bucket, indent=2), encoding="utf-8")


    def poo(self):
        print("WEEEEEEE")  

def SetupPageDictionary(PageViewControllerList):
    PagesDict = PageDictionaryTemplate
    PageDictionaryTemplate["Home"]["ViewController"]          = PageViewControllerList[0] # Home
    PageDictionaryTemplate["ServerHome"]["ViewController"]    = PageViewControllerList[1] # ServerHome
    PageDictionaryTemplate["EditServer"][3]["ViewController"] = PageViewControllerList[2] # EditServer
    PageDictionaryTemplate["EditServer"][1]["ViewController"] = PageViewControllerList[2] # NewServer
    PageDictionaryTemplate["Settings"]["ViewController"]      = PageViewControllerList[3] # Settings

    return PagesDict    







def DebugPrint(msg, fromprocess=None, warn=False, alert=False, info=False, overide=False, multi=None):  #My own utility for debug msgs
    if VERBOSE or DEVMODE or overide or warn or alert or info:
        if warn:
            starter=colored("[WARN] ", ApplyTextStyles["warnTextColor"], attrs=['bold'])
        elif alert:
            starter=colored("[ALERT]", ApplyTextStyles["textColor"], ApplyTextStyles["alertBGColor"])
        elif info: 
            starter=colored("[INFO] ", ApplyTextStyles["infoTextColor"], attrs=['bold'])
        else:
            starter=colored("[DEBUG]", ApplyTextStyles["debugTextColor"] , attrs=['bold'])

        now = datetime.now()
        debugtime = colored("[" + now.strftime("%m/%d %I:%M.%S") + "]", ApplyTextStyles["timeColor"]) + colored(" | ", ApplyTextStyles["debugTextColor"])

        if fromprocess == "sf":
            fromprocess = colored((fromprocess.strip(".py")+"/support/support_functions.py"), ApplyTextStyles["processColor"])

        if fromprocess:
            fromprocess = colored("*" + fromprocess, ApplyTextStyles["processColor"]) 

        if fromprocess is ApplyTextStyles["LastDebugPrintProcess"] or fromprocess is None:
            print("{}{} {}".format(starter, debugtime, msg))
        else:
            print("{}{} {}   {})".format(starter, debugtime, msg, fromprocess))
            #print(" + {} [{}]".format(msg, debugtime))
        LastDebugPrintProcess = fromprocess

        spacer = "                        "

        if type(multi) == list:
            for x in range(len(multi)):
                print(colored("{}--> {}".format(spacer,multi[x]), ApplyTextStyles["textColor"]))

def secure_random_digits(x):
    return ''.join(str(secrets.randbelow(10)) for _ in range(x))

def GenUUID(name):
        now = datetime.now()
        timePart = base64.b64encode(str(now.strftime("%m%d%y")).encode()).decode().strip("=")
        namePart = base64.b64encode(name.encode()).decode().strip("=")
        mainPart = namePart + "=" + timePart

        uuidlen = len(mainPart)
        if uuidlen < 32:
            pading = base64.b64encode(secure_random_digits(32).encode()).decode()[:32]
            out = mainPart + "=" + pading[:(32 - uuidlen) -1]
        elif uuidlen >= 32:
            over = (32 - len(timePart) - 1)
            out = namePart[:over] + "=" + timePart


        DebugPrint("Generated UUID: {}".format(out), "main._gen_uuid")
        return out

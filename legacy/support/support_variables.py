# ===================  Misc vars =================== ##
VER = "0.1"                 # This Softwares Version
#SHOW_CONSOLE_OUTPUT = False                # Show the console output when 'make' is called?
VERBOSE = True
DEVMODE = True

LastDebugPrintProcess = ""
SectServers = "Servers"

RealPageList = ["Home", "ServerHome", "NewServer", "EditServer", "Settings"]

PageDictionaryTemplate = {
        "Home": [
                ("Index", 0),
                ("ViewController", ""),
                ("Functions", [{
                        "Test": "home.test"
                }]),
        ],
        "ServerHome": [
                ("Index", 1),
                ("ViewController", ""),
                ("Functions", [{
                        "Test": "home.test"
                }]),
        ],
        "EditServer": [
                ("NewServer", {
                        "Index": 2,
                        "ViewController": "",
                        "Functions": [{
                                "Save": "servers.save",
                                "Cancel": "servers.cancel"
                        }]
                }),
                ("EditServer", {
                        "Index": 3,
                        "ViewController": "",
                        "Functions": [{
                                "Save": "servers.save",
                                "Delete": "servers.delete",
                                "Cancel": "servers.cancel"
                        }]
                }),
        ],
        "Settings": [
                ("Index", 4),
                ("ViewController", ""),
                ("Functions", [{
                        "Test": "home.test"
                }]),
        ]
}

ApplyTextStyles = {
        "LastDebugPrintProcess" : 0,
        "warnTextColor" : (181, 128, 0),
        "infoTextColor" : (76, 231,0),
        "alertBGColor" : (151,83,83),
        "debugTextColor" : (1,127,179),
        "timeColor" : (105,105,105),        
        "processColor" : (60,106,0),
        "textColor" : (255,255,255)
}


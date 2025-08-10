KoPID_from_partKoPName = {
    'Detector Unit' : 2407,
    'Detector' : 2414,
    'Module' : 1005,
    'Slot' : 2412,
    'PEB' : 2410,
    'Flex Tail' : 2409,
    'Hybrid' : 1003,
    'Module Flex' : 1004
}

# hardcoded part ids for testing parts (HGTD Database test)
partIDs_for_Testing = {
    'Detector Unit' : 28815,
    'Detector' : 6553,
    'Module' : 6573,
    #'Slot' : 
}

# define module geometry for canvas - not to scale!!!
modLongSide = 80
modShortSide = 40

# define slots - not to scale!!!
modR1M1 = {'slot':"R1M1", 'x':60, 'y':60, 'w':modLongSide, 'h':modShortSide}
modR2M1 = {'slot':"R2M1", 'x':160, 'y':60, 'w':modLongSide, 'h':modShortSide}
modR3M1 = {'slot':"R3M1", 'x':260, 'y':60, 'w':modLongSide, 'h':modShortSide}

modR1M2 = {'slot':"R1M2", 'x':60, 'y':120, 'w':modLongSide, 'h':modShortSide}
modR2M2 = {'slot':"R2M2", 'x':160, 'y':120, 'w':modLongSide, 'h':modShortSide}
modR3M2 = {'slot':"R3M2", 'x':260, 'y':120, 'w':modLongSide, 'h':modShortSide}

modR1M3 = {'slot':"R1M3", 'x':60, 'y':180, 'w':modLongSide, 'h':modShortSide}
modR2M3 = {'slot':"R2M3", 'x':160, 'y':180, 'w':modLongSide, 'h':modShortSide}
modR3M3 = {'slot':"R3M3", 'x':260, 'y':180, 'w':modLongSide, 'h':modShortSide}

modR1M4 = {'slot':"R1M4", 'x':60, 'y':240, 'w':modLongSide, 'h':modShortSide}
modR2M4 = {'slot':"R2M4", 'x':160, 'y':240, 'w':modLongSide, 'h':modShortSide}
modR3M4 = {'slot':"R3M4", 'x':260, 'y':240, 'w':modLongSide, 'h':modShortSide}

modR1M5 = {'slot':"R1M5", 'x':60, 'y':300, 'w':modLongSide, 'h':modShortSide}
modR2M5 = {'slot':"R2M5", 'x':160, 'y':300, 'w':modLongSide, 'h':modShortSide}
modR3M5 = {'slot':"R3M5", 'x':260, 'y':300, 'w':modLongSide, 'h':modShortSide}

modR1M6 = {'slot':"R1M6", 'x':60, 'y':360, 'w':modLongSide, 'h':modShortSide}
modR2M6 = {'slot':"R2M6", 'x':160, 'y':360, 'w':modLongSide, 'h':modShortSide}
modR3M6 = {'slot':"R3M6", 'x':260, 'y':360, 'w':modLongSide, 'h':modShortSide}

modR1M7 = {'slot':"R1M7", 'x':60, 'y':420, 'w':modLongSide, 'h':modShortSide}
modR2M7 = {'slot':"R2M7", 'x':160, 'y':420, 'w':modLongSide, 'h':modShortSide}
modR3M7 = {'slot':"R3M7", 'x':260, 'y':420, 'w':modLongSide, 'h':modShortSide}

modROTATER2M1 = {'slot':"R2M1", 'x':160, 'y':120, 'w':modShortSide, 'h':modLongSide}
modROTATER2M2 = {'slot':"R2M2", 'x':100, 'y':120, 'w':modShortSide, 'h':modLongSide}

# define DUs - not to scale!!!
allDUs = {
    "BI01":[modR1M1, modR1M2, modR1M3,
            modR2M1, modR2M2, modR2M3, modR2M4,
            modR3M1, modR3M2, modR3M3, modR3M4],
    "BI10":[modR1M1, modR1M2],
    "BI12":[modR1M1, modR1M2, modR1M3, modR1M4,
            modR2M1, modR2M2, modR2M3, modR2M4,
            modR3M1, modR3M2, modR3M3, modR3M4],
    "BM01":[modR1M1, modR1M2, modR1M3, modR1M4, modR1M5,
            modR2M1, modR2M2, modR2M3, modR2M4, modR2M5,
            modR3M1, modR3M2, modR3M3, modR3M4],
    "BM02":[modR1M1, modR1M2, modR1M3, modR1M4,
            modR2M1, modR2M2, modR2M3, modR2M4,
            modR3M1, modR3M2, modR3M3, modR3M4, modR3M5],
    "BM03":[modR1M1, modR1M2, modR1M3,
            modR2M1, modR2M2, modR2M3, modR2M4, modR2M5],
    "BM04":[modR1M1, modR1M2, modR1M3, modR1M4,
            modR2M1, modR2M2, modR2M3, modR2M4],
    "BM05":[modR1M1, modR1M2, modR1M3,
            modR2M1, modR2M2, modR2M3, modR2M4, modR2M5],
    "BM06":[modR1M1, modR1M2],
    "BM08":[modR1M1, modR1M2, modR1M3, modR1M4, modR1M5,
            modR2M1, modR2M2, modR2M3, modR2M4, modR2M5],
    "BM09":[modR1M1, modR1M2, modR1M3,
            modR2M1, modR2M2, modR2M3,
            modR3M1, modR3M2],
    "BM10":[modR1M1, modR1M2, modR1M3, modR1M4, modR1M5, modR1M6,
            modR2M1, modR2M2, modR2M3, modR2M4, modR2M5, modR2M6],
    "BM11":[modR1M1, modR1M2, modR1M3, modR1M4,
            modR2M1, modR2M2, modR2M3, modR2M4,
            modR3M1, modR3M2, modR3M3, modR3M4, modR3M5],
    "BM12":[modR1M1, modR1M2, modR1M3, modR1M4, modR1M5,
            modR2M1, modR2M2, modR2M3, modR2M4, modR2M5,
            modR3M1, modR3M2, modR3M3, modR3M4],
    "BO01":[modR1M1, modR1M2, modR1M3, modR1M4, modR1M5,
            modR2M1, modR2M2, modR2M3, modR2M4, modR2M5,
            modR3M1, modR3M2, modR3M3, modR3M4, modR3M5],
    "BO02":[modR1M1, modR1M2, modR1M3, modR1M4, modR1M5, modR1M6,
            modR2M1, modR2M2, modR2M3, modR2M4, modR2M5, modR2M6],
    "BO03":[modR1M1, modR1M2, modR1M3, modR1M4, modR1M5, modR1M6,
            modR2M1, modR2M2, modR2M3, modR2M4, modR2M5, modR2M6],
    "BO04":[modR1M1, modR1M2,
            modR2M1, modR2M2, modR2M3, modR2M4,
            modR3M1, modR3M2, modR3M3, modR3M4],
    "BO05":[modR1M1, modR1M2, modR1M3, modR1M4, modR1M5,
            modR2M1, modR2M2, modR2M3, modR2M4,
            modR3M1, modR3M2, modR3M3],
    "BO06":[modR1M1, modR1M2, modR1M3, modR1M4, modR1M5,
            modR2M1, modR2M2, modR2M3, modR2M4, modR2M5, modR2M6],
    "BO07":[modR1M1,
            modR2M1, modR2M2, modR2M3],
    "BO08":[modR1M1, modR1M2, modR1M3, modR1M4, modR1M5, modR1M6,
            modR2M1, modR2M2, modR2M3, modR2M4, modR2M5, modR2M6],
    "BO10":[modR1M1, modR1M2, modR1M3, modR1M4, modR1M5, modR1M6,
            modR2M1, modR2M2, modR2M3, modR2M4, modR2M5, modR2M6],
    "BO12":[modR1M1, modR1M2, modR1M3, modR1M4, modR1M5,
            modR2M1, modR2M2, modR2M3, modR2M4, modR2M5,
            modR3M1, modR3M2, modR3M3, modR3M4, modR3M5, modR3M6],
    "FI01":[modR1M1, modR1M2, modR1M3, modR1M4,
            modR2M1, modR2M2, modR2M3, modR2M4,
            modR3M1, modR3M2, modR3M3, modR3M4],
    "FI10":[modR1M1,
            modROTATER2M1, modROTATER2M2],
    "FI12":[modR1M1, modR1M2, modR1M3, modR1M4,
            modR2M1, modR2M2, modR2M3, modR2M4,
            modR3M1, modR3M2, modR3M3, modR3M4],
    "FM01":[modR1M1, modR1M2, modR1M3, modR1M4, modR1M5,
            modR2M1, modR2M2, modR2M3, modR2M4, modR2M5,
            modR3M1, modR3M2, modR3M3, modR3M4, modR3M5],
    "FM02":[modR1M1, modR1M2, modR1M3, modR1M4,
            modR2M1, modR2M2, modR2M3, modR2M4,
            modR3M1, modR3M2, modR3M3, modR3M4],
    "FM03":[modR1M1, modR1M2, modR1M3, modR1M4, modR1M5,
            modR2M1, modR2M2, modR2M3, modR2M4],
    "FM04":[modR1M1, modR1M2, modR1M3, modR1M4,
            modR2M1, modR2M2, modR2M3, modR2M4],
    "FM05":[modR1M1, modR1M2, modR1M3, modR1M4, modR1M5, modR1M6,
            modR2M1, modR2M2, modR2M3, modR2M4],
    "FM06":[modR1M1, modR1M2],
    "FM08":[modR1M1, modR1M2, modR1M3, modR1M4, modR1M5,
            modR2M1, modR2M2, modR2M3, modR2M4, modR2M5, modR2M6, modR2M7],
    "FM09":[modR1M1, modR1M2, modR1M3, modR1M4,
            modR2M1, modR2M2, modR2M3, modR2M4],
    "FM10":[modR1M1, modR1M2, modR1M3, modR1M4, modR1M5,
            modR2M1, modR2M2, modR2M3, modR2M4, modR2M5],
    "FM11":[modR1M1, modR1M2, modR1M3, modR1M4, modR1M5,
            modR2M1, modR2M2, modR2M3, modR2M4, modR2M5,
            modR3M1, modR3M2, modR3M3, modR3M4],
    "FM12":[modR1M1, modR1M2, modR1M3, modR1M4,
            modR2M1, modR2M2, modR2M3, modR2M4,
            modR3M1, modR3M2, modR3M3, modR3M4, modR3M5],
    "FO01":[modR1M1, modR1M2, modR1M3, modR1M4, modR1M5,
            modR2M1, modR2M2, modR2M3, modR2M4, modR2M5,
            modR3M1, modR3M2, modR3M3, modR3M4, modR3M5],
    "FO02":[modR1M1, modR1M2, modR1M3, modR1M4, modR1M5, modR1M6,
            modR2M1, modR2M2, modR2M3, modR2M4, modR2M5, modR2M6],
    "FO03":[modR1M1, modR1M2, modR1M3, modR1M4, modR1M5, modR1M6,
            modR2M1, modR2M2, modR2M3, modR2M4, modR2M5, modR2M6],
    "FO04":[modR1M1, modR1M2, modR1M3, modR1M4,
            modR2M1, modR2M2, modR2M3, modR2M4,
            modR3M1, modR3M2, modR3M3],
    "FO05":[modR1M1, modR1M2,
            modR2M1, modR2M2, modR2M3, modR2M4,
            modR3M1, modR3M2, modR3M3, modR3M4],
    "FO06":[modR1M1, modR1M2, modR1M3, modR1M4, modR1M5, modR1M6,
            modR2M1, modR2M2, modR2M3, modR2M4, modR2M5],
    "FO07":[modR1M1, modR1M2, modR1M3, modR1M4,
            modR2M1],
    "FO08":[modR1M1, modR1M2, modR1M3, modR1M4, modR1M5,
            modR2M1, modR2M2, modR2M3, modR2M4, modR2M5],
    "FO10":[modR1M1, modR1M2, modR1M3, modR1M4, modR1M5,
            modR2M1, modR2M2, modR2M3, modR2M4, modR2M5],
    "FO12":[modR1M1, modR1M2, modR1M3, modR1M4, modR1M5,
            modR2M1, modR2M2, modR2M3, modR2M4, modR2M5,
            modR3M1, modR3M2, modR3M3, modR3M4, modR3M5],
}

totalNModules = 0
allDUkeysStr = ''
for key in allDUs.keys():
    allDUkeysStr += f"{key},";
    totalNModules += len(allDUs[key])

allPEBs = ['1F', '1B', '2F', '2B', '3F', '3B']
F_PEBs = ['1F', '1B', '2F', '2B', '3F']
B_PEBs = ['1F', '1B', '2F', '2B', '3B']

fillColor_SU = '#f4f4bb'
fillColor_Slot = '#ffffff'
fillColor_SU_Text = '#aaaaaa'
fillColor_AlreadyLoadedSlot = '#00ddff'
fillColor_ActiveSlot = '#33ff33'

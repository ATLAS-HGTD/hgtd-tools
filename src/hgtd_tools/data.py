# This file contains all hardcoded constants
## For reporting
all_cats = [
    "Sensor",
    "Wafer",
    "ASIC",
    "Hybrid",
    "Module Flex",
    "Module",
    "Support Unit",
    "Detector Unit",
    "PEB",
    "PEB_MUX64",
    "Flex Tail",
    "HV_PS",
    "HV_module",
]
public_cats = [
    "Sensor",
    "Wafer",
    # "ASIC", add them back when significant portion is uploaded
    "Hybrid",
    "Module Flex",
    "Module",
    "Support Unit",
    "Detector Unit",
    "PEB",
    # "PEB_MUX64", add them back when significant portion is uploaded
    "Flex Tail",
    "HV_PS",
    "HV_module",
]
test_cats = [
    "HV_PS",
    "HV_module",
]
## DB internal IDs
### human-readable KoP name map to internal KoP-ID
KoPID_from_partKoPName = {
    "Sensor": 1000,
    "Wafer": 1001,
    "ASIC": 1002,
    "Hybrid": 1003,
    "Module Flex": 1004,
    "Module": 1005,
    "Detector Unit": 2407,
    "Support Unit": 2408,
    "Flex Tail": 2409,
    "PEB": 2410,
    "VTRx": 2411,
    "Slot": 2412,
    "Detector": 2414,
    "PEB_MUX64": 2415,
    "HV_PS": 2416,
    "HV_module": 2417,
}
### hardcoded part ids for testing parts (HGTD Database test)
partIDs_for_Testing = {
    "Detector Unit": 28815,
    "Detector": 6553,
    "Module": 6573,
}
### real detector parent part (its part_id)
partID_parent_Detector = 28833
### human-readable locations map to ID
relevant_location_IDs_by_shortname = {
    "ifae": 1,
    "ihep": 1401,
    "ijclab": 1122,
    "lpnhe": 1501,
    "mainz": 1481,
    "mascir": 1581,
    "ustc": 1441,
    "cern": 1541,  # clean room, where tests are done
    "test": 1521,
}
### human-readable manufacturers map to ID
relevant_manufacturer_IDs_by_shortname = {
    "ifae": 1003,
    "ihep": 1004,
    "ijclab": 1061,
    "mainz": 1141,
    "mascir": 1241,
    "ustc": 1261,
    "test": 1161,
    "IHEP-IME": 1021,
    "USTC-IME": 1041,
}
## Serial Number decoding / encoding helpers
### defintion of chars in MO SNs: site
MO_site_id = {
    "ifae": "F",
    "ihep": "H",
    "ijclab": "J",
    "mainz": "M",
    "mascir": "A",
    "ustc": "U",
    "test": "T",
}
MA_sites_to_monitor = ["ifae", "ihep", "ijclab", "mainz", "mascir"]
HY_sites_to_monitor = ["ifae", "ihep"]
S_W_manus_to_monitor = ["IHEP-IME", "USTC-IME"]
### defintion of chars in MO SNs: prod
MO_prod_id = {
    "prod": "M",  # main production
    "preprod": "P",  # preproduction
    "demo": "D",  # demonstrator
    "test": "T",  # test
    "other": "O",  # other
}
## Slots and their graphical representation
### define module geometry for canvas - not to scale!!!
modLongSide = 80
modShortSide = 40
### define slots - not to scale!!!
modR1M1 = {"slot": "R1M1", "x": 60, "y": 60, "w": modLongSide, "h": modShortSide}
modR2M1 = {"slot": "R2M1", "x": 160, "y": 60, "w": modLongSide, "h": modShortSide}
modR3M1 = {"slot": "R3M1", "x": 260, "y": 60, "w": modLongSide, "h": modShortSide}

modR1M2 = {"slot": "R1M2", "x": 60, "y": 120, "w": modLongSide, "h": modShortSide}
modR2M2 = {"slot": "R2M2", "x": 160, "y": 120, "w": modLongSide, "h": modShortSide}
modR3M2 = {"slot": "R3M2", "x": 260, "y": 120, "w": modLongSide, "h": modShortSide}

modR1M3 = {"slot": "R1M3", "x": 60, "y": 180, "w": modLongSide, "h": modShortSide}
modR2M3 = {"slot": "R2M3", "x": 160, "y": 180, "w": modLongSide, "h": modShortSide}
modR3M3 = {"slot": "R3M3", "x": 260, "y": 180, "w": modLongSide, "h": modShortSide}

modR1M4 = {"slot": "R1M4", "x": 60, "y": 240, "w": modLongSide, "h": modShortSide}
modR2M4 = {"slot": "R2M4", "x": 160, "y": 240, "w": modLongSide, "h": modShortSide}
modR3M4 = {"slot": "R3M4", "x": 260, "y": 240, "w": modLongSide, "h": modShortSide}

modR1M5 = {"slot": "R1M5", "x": 60, "y": 300, "w": modLongSide, "h": modShortSide}
modR2M5 = {"slot": "R2M5", "x": 160, "y": 300, "w": modLongSide, "h": modShortSide}
modR3M5 = {"slot": "R3M5", "x": 260, "y": 300, "w": modLongSide, "h": modShortSide}

modR1M6 = {"slot": "R1M6", "x": 60, "y": 360, "w": modLongSide, "h": modShortSide}
modR2M6 = {"slot": "R2M6", "x": 160, "y": 360, "w": modLongSide, "h": modShortSide}
modR3M6 = {"slot": "R3M6", "x": 260, "y": 360, "w": modLongSide, "h": modShortSide}

modR1M7 = {"slot": "R1M7", "x": 60, "y": 420, "w": modLongSide, "h": modShortSide}
modR2M7 = {"slot": "R2M7", "x": 160, "y": 420, "w": modLongSide, "h": modShortSide}
modR3M7 = {"slot": "R3M7", "x": 260, "y": 420, "w": modLongSide, "h": modShortSide}

modROTATER2M1 = {
    "slot": "R2M1",
    "x": 160,
    "y": 120,
    "w": modShortSide,
    "h": modLongSide,
}
modROTATER2M2 = {
    "slot": "R2M2",
    "x": 100,
    "y": 120,
    "w": modShortSide,
    "h": modLongSide,
}
### define DUs - not to scale!!!
allDUs = {
    "BI01": [
        modR1M1,
        modR1M2,
        modR1M3,
        modR2M1,
        modR2M2,
        modR2M3,
        modR2M4,
        modR3M1,
        modR3M2,
        modR3M3,
        modR3M4,
    ],
    "BI10": [modR1M1, modR1M2],
    "BI12": [
        modR1M1,
        modR1M2,
        modR1M3,
        modR1M4,
        modR2M1,
        modR2M2,
        modR2M3,
        modR2M4,
        modR3M1,
        modR3M2,
        modR3M3,
        modR3M4,
    ],
    "BM01": [
        modR1M1,
        modR1M2,
        modR1M3,
        modR1M4,
        modR1M5,
        modR2M1,
        modR2M2,
        modR2M3,
        modR2M4,
        modR2M5,
        modR3M1,
        modR3M2,
        modR3M3,
        modR3M4,
    ],
    "BM02": [
        modR1M1,
        modR1M2,
        modR1M3,
        modR1M4,
        modR2M1,
        modR2M2,
        modR2M3,
        modR2M4,
        modR3M1,
        modR3M2,
        modR3M3,
        modR3M4,
        modR3M5,
    ],
    "BM03": [modR1M1, modR1M2, modR1M3, modR2M1, modR2M2, modR2M3, modR2M4, modR2M5],
    "BM04": [modR1M1, modR1M2, modR1M3, modR1M4, modR2M1, modR2M2, modR2M3, modR2M4],
    "BM05": [modR1M1, modR1M2, modR1M3, modR2M1, modR2M2, modR2M3, modR2M4, modR2M5],
    "BM06": [modR1M1, modR1M2],
    "BM08": [
        modR1M1,
        modR1M2,
        modR1M3,
        modR1M4,
        modR1M5,
        modR2M1,
        modR2M2,
        modR2M3,
        modR2M4,
        modR2M5,
    ],
    "BM09": [modR1M1, modR1M2, modR1M3, modR2M1, modR2M2, modR2M3, modR3M1, modR3M2],
    "BM10": [
        modR1M1,
        modR1M2,
        modR1M3,
        modR1M4,
        modR1M5,
        modR1M6,
        modR2M1,
        modR2M2,
        modR2M3,
        modR2M4,
        modR2M5,
        modR2M6,
    ],
    "BM11": [
        modR1M1,
        modR1M2,
        modR1M3,
        modR1M4,
        modR2M1,
        modR2M2,
        modR2M3,
        modR2M4,
        modR3M1,
        modR3M2,
        modR3M3,
        modR3M4,
        modR3M5,
    ],
    "BM12": [
        modR1M1,
        modR1M2,
        modR1M3,
        modR1M4,
        modR1M5,
        modR2M1,
        modR2M2,
        modR2M3,
        modR2M4,
        modR2M5,
        modR3M1,
        modR3M2,
        modR3M3,
        modR3M4,
    ],
    "BO01": [
        modR1M1,
        modR1M2,
        modR1M3,
        modR1M4,
        modR1M5,
        modR2M1,
        modR2M2,
        modR2M3,
        modR2M4,
        modR2M5,
        modR3M1,
        modR3M2,
        modR3M3,
        modR3M4,
        modR3M5,
    ],
    "BO02": [
        modR1M1,
        modR1M2,
        modR1M3,
        modR1M4,
        modR1M5,
        modR1M6,
        modR2M1,
        modR2M2,
        modR2M3,
        modR2M4,
        modR2M5,
        modR2M6,
    ],
    "BO03": [
        modR1M1,
        modR1M2,
        modR1M3,
        modR1M4,
        modR1M5,
        modR1M6,
        modR2M1,
        modR2M2,
        modR2M3,
        modR2M4,
        modR2M5,
        modR2M6,
    ],
    "BO04": [
        modR1M1,
        modR1M2,
        modR2M1,
        modR2M2,
        modR2M3,
        modR2M4,
        modR3M1,
        modR3M2,
        modR3M3,
        modR3M4,
    ],
    "BO05": [
        modR1M1,
        modR1M2,
        modR1M3,
        modR1M4,
        modR1M5,
        modR2M1,
        modR2M2,
        modR2M3,
        modR2M4,
        modR3M1,
        modR3M2,
        modR3M3,
    ],
    "BO06": [
        modR1M1,
        modR1M2,
        modR1M3,
        modR1M4,
        modR1M5,
        modR2M1,
        modR2M2,
        modR2M3,
        modR2M4,
        modR2M5,
        modR2M6,
    ],
    "BO07": [modR1M1, modR2M1, modR2M2, modR2M3],
    "BO08": [
        modR1M1,
        modR1M2,
        modR1M3,
        modR1M4,
        modR1M5,
        modR1M6,
        modR2M1,
        modR2M2,
        modR2M3,
        modR2M4,
        modR2M5,
        modR2M6,
    ],
    "BO10": [
        modR1M1,
        modR1M2,
        modR1M3,
        modR1M4,
        modR1M5,
        modR1M6,
        modR2M1,
        modR2M2,
        modR2M3,
        modR2M4,
        modR2M5,
        modR2M6,
    ],
    "BO12": [
        modR1M1,
        modR1M2,
        modR1M3,
        modR1M4,
        modR1M5,
        modR2M1,
        modR2M2,
        modR2M3,
        modR2M4,
        modR2M5,
        modR3M1,
        modR3M2,
        modR3M3,
        modR3M4,
        modR3M5,
        modR3M6,
    ],
    "FI01": [
        modR1M1,
        modR1M2,
        modR1M3,
        modR1M4,
        modR2M1,
        modR2M2,
        modR2M3,
        modR2M4,
        modR3M1,
        modR3M2,
        modR3M3,
        modR3M4,
    ],
    "FI10": [modR1M1, modROTATER2M1, modROTATER2M2],
    "FI12": [
        modR1M1,
        modR1M2,
        modR1M3,
        modR1M4,
        modR2M1,
        modR2M2,
        modR2M3,
        modR2M4,
        modR3M1,
        modR3M2,
        modR3M3,
        modR3M4,
    ],
    "FM01": [
        modR1M1,
        modR1M2,
        modR1M3,
        modR1M4,
        modR1M5,
        modR2M1,
        modR2M2,
        modR2M3,
        modR2M4,
        modR2M5,
        modR3M1,
        modR3M2,
        modR3M3,
        modR3M4,
        modR3M5,
    ],
    "FM02": [
        modR1M1,
        modR1M2,
        modR1M3,
        modR1M4,
        modR2M1,
        modR2M2,
        modR2M3,
        modR2M4,
        modR3M1,
        modR3M2,
        modR3M3,
        modR3M4,
    ],
    "FM03": [
        modR1M1,
        modR1M2,
        modR1M3,
        modR1M4,
        modR1M5,
        modR2M1,
        modR2M2,
        modR2M3,
        modR2M4,
    ],
    "FM04": [modR1M1, modR1M2, modR1M3, modR1M4, modR2M1, modR2M2, modR2M3, modR2M4],
    "FM05": [
        modR1M1,
        modR1M2,
        modR1M3,
        modR1M4,
        modR1M5,
        modR1M6,
        modR2M1,
        modR2M2,
        modR2M3,
        modR2M4,
    ],
    "FM06": [modR1M1, modR1M2],
    "FM08": [
        modR1M1,
        modR1M2,
        modR1M3,
        modR1M4,
        modR1M5,
        modR2M1,
        modR2M2,
        modR2M3,
        modR2M4,
        modR2M5,
        modR2M6,
        modR2M7,
    ],
    "FM09": [modR1M1, modR1M2, modR1M3, modR1M4, modR2M1, modR2M2, modR2M3, modR2M4],
    "FM10": [
        modR1M1,
        modR1M2,
        modR1M3,
        modR1M4,
        modR1M5,
        modR2M1,
        modR2M2,
        modR2M3,
        modR2M4,
        modR2M5,
    ],
    "FM11": [
        modR1M1,
        modR1M2,
        modR1M3,
        modR1M4,
        modR1M5,
        modR2M1,
        modR2M2,
        modR2M3,
        modR2M4,
        modR2M5,
        modR3M1,
        modR3M2,
        modR3M3,
        modR3M4,
    ],
    "FM12": [
        modR1M1,
        modR1M2,
        modR1M3,
        modR1M4,
        modR2M1,
        modR2M2,
        modR2M3,
        modR2M4,
        modR3M1,
        modR3M2,
        modR3M3,
        modR3M4,
        modR3M5,
    ],
    "FO01": [
        modR1M1,
        modR1M2,
        modR1M3,
        modR1M4,
        modR1M5,
        modR2M1,
        modR2M2,
        modR2M3,
        modR2M4,
        modR2M5,
        modR3M1,
        modR3M2,
        modR3M3,
        modR3M4,
        modR3M5,
    ],
    "FO02": [
        modR1M1,
        modR1M2,
        modR1M3,
        modR1M4,
        modR1M5,
        modR1M6,
        modR2M1,
        modR2M2,
        modR2M3,
        modR2M4,
        modR2M5,
        modR2M6,
    ],
    "FO03": [
        modR1M1,
        modR1M2,
        modR1M3,
        modR1M4,
        modR1M5,
        modR1M6,
        modR2M1,
        modR2M2,
        modR2M3,
        modR2M4,
        modR2M5,
        modR2M6,
    ],
    "FO04": [
        modR1M1,
        modR1M2,
        modR1M3,
        modR1M4,
        modR2M1,
        modR2M2,
        modR2M3,
        modR2M4,
        modR3M1,
        modR3M2,
        modR3M3,
    ],
    "FO05": [
        modR1M1,
        modR1M2,
        modR2M1,
        modR2M2,
        modR2M3,
        modR2M4,
        modR3M1,
        modR3M2,
        modR3M3,
        modR3M4,
    ],
    "FO06": [
        modR1M1,
        modR1M2,
        modR1M3,
        modR1M4,
        modR1M5,
        modR1M6,
        modR2M1,
        modR2M2,
        modR2M3,
        modR2M4,
        modR2M5,
    ],
    "FO07": [modR1M1, modR1M2, modR1M3, modR1M4, modR2M1],
    "FO08": [
        modR1M1,
        modR1M2,
        modR1M3,
        modR1M4,
        modR1M5,
        modR2M1,
        modR2M2,
        modR2M3,
        modR2M4,
        modR2M5,
    ],
    "FO10": [
        modR1M1,
        modR1M2,
        modR1M3,
        modR1M4,
        modR1M5,
        modR2M1,
        modR2M2,
        modR2M3,
        modR2M4,
        modR2M5,
    ],
    "FO12": [
        modR1M1,
        modR1M2,
        modR1M3,
        modR1M4,
        modR1M5,
        modR2M1,
        modR2M2,
        modR2M3,
        modR2M4,
        modR2M5,
        modR3M1,
        modR3M2,
        modR3M3,
        modR3M4,
        modR3M5,
    ],
}

# From Slot Table (per quadrant)
# Generated here: https://gitlab.cern.ch/anstein/slotsflextailspreproduction/-/blob/master/SlotTable/slotTableGenerator.ipynb?ref_type=heads
DU_Interlock_dict = {
    "BI01": ["R3M4", "R1M2"],
    "BI10": [],
    "BI12": ["R2M4", "R1M1"],
    "BM01": ["R2M3"],
    "BM02": ["R3M4"],
    "BM03": ["R1M2"],
    "BM04": ["R2M2"],
    "BM05": ["R1M2"],
    "BM06": [],
    "BM08": ["R2M2"],
    "BM09": ["R1M2"],
    "BM10": ["R2M4"],
    "BM11": ["R2M2"],
    "BM12": ["R2M3"],
    "BO01": ["R2M5"],
    "BO02": ["R2M2"],
    "BO03": ["R2M5", "R1M2"],
    "BO04": ["R2M2"],
    "BO05": ["R2M2"],
    "BO06": ["R2M3"],
    "BO07": ["R2M2"],
    "BO08": ["R2M4", "R1M1"],
    "BO10": ["R1M6"],
    "BO12": ["R3M2", "R1M4"],
    "FI01": ["R1M1", "R2M4"],
    "FI10": [],
    "FI12": ["R1M2", "R3M4"],
    "FM01": ["R2M3"],
    "FM02": ["R2M3"],
    "FM03": ["R1M4"],
    "FM04": ["R2M4"],
    "FM05": ["R2M2"],
    "FM06": [],
    "FM08": ["R1M3"],
    "FM09": ["R1M2"],
    "FM10": ["R2M3"],
    "FM11": ["R2M3"],
    "FM12": ["R3M4"],
    "FO01": ["R1M4", "R3M2"],
    "FO02": ["R1M6"],
    "FO03": ["R1M1", "R2M4"],
    "FO04": ["R2M4", "R3M1"],
    "FO05": ["R3M3"],
    "FO06": ["R2M2"],
    "FO07": [],
    "FO08": ["R1M2", "R2M5"],
    "FO10": ["R2M2"],
    "FO12": ["R2M5", "R3M2"],
}

## Keys for DU, PEB

### DU keys
totalNModules = 0
allDUkeysStr = ""
for key in allDUs.keys():
    allDUkeysStr += f"{key},"
    totalNModules += len(allDUs[key])
allDUkeysList = list(allDUs.keys())
### PEB keys
allPEBs = ["1F", "1B", "2F", "2B", "3F", "3B"]
F_PEBs = ["1F", "1B", "2F", "2B", "3F"]
B_PEBs = ["1F", "1B", "2F", "2B", "3B"]

## Color scheme for GUI

### slot colors in DU view
fillColor_SU = "#f4f4bb"
fillColor_Slot = "#FFFFFF"
fillColor_SU_Text = "#aaaaaa"
fillColor_InterlockSlot = "#840032"  # "#420019"#"#ffaaaa"
fillColor_AlreadyLoadedSlot = "#b4adea"  # "#d9dbff"#"#3066be"#"#00ddff"
fillColor_ActiveSlot = "#edc273"  # "#E5A93B"#"#D4A373"#"#e396df"#"#33ff33"

### standard buttons
fg_color_standard_but_active = "#339941"
hover_color_standard_but_active = "#228831"
fg_color_standard_but_inactive = "#555555"
hover_color_standard_but_inactive = "#444444"
fg_color_standard_but_red = "#cf352e"
hover_color_standard_but_red = "#B02B25"

### progress bar
progress_color_OK = "#007711"
progress_color_wait = "#BBAA00"
progress_color_ERROR = "#ff0000"


## Electrical properties
module_flex_ohm_res = 11000

<div align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="./windowIcon.png">
    <img src="./windowIcon.png" width=240>
  </picture>
</div>

<div align="center">
    
![Static Badge](https://img.shields.io/badge/python-3.12-blue)

</div>

## Description
These tools interact with the HGTD Production Database for the HGTD Phase-II Upgrade of the ATLAS Experiment at CERN.

### Features
- API
- GUI
- Module Loading
- Detector Assembly (CERN)

### Already working
- Selecting and writing parent / child relations with a GUI: canvas to select slots for modules for Module Loading, form data will be processed via "click" position
- Search through partstree and slots to perform multiple POST requests in one go: Detector Assembly (CERN) puts DU on Detector, loaded Modules get Slots
- Uses standard coordinate system for global attributes: Vessel, Layer, Quadrant, DU type / SU type, Row (global), Module (global) and can map to local attributes: Row (on DU), Module (on DU)
- Support for all 48 DU types, including those that have "horizontal" and "vertical" modules on the same unit
- Loaded modules are shown as green slots when doing Detector Assembly (CERN)
- If DU is already placed in detector, show where it is (Vessel / Layer / Quadrant)
- Catch wrong VLQ entries knowing which combinations are allowed
- Delete request for all existing slots for loaded modules (propagate new VLQ) when new Detector Assembly (CERN) operation is initiated with another VLQ, i.e. effectively replace with new ones
- API request status is updating while thread is running, progressbar fill wiht different colors

### Open points requiring implementation
- (~!!! Replace local files with API-requested files (only few more parts missing, most are already dynamically retrieved)~ first implementation done, being tested (probably a bit slow), second implementation does not need to get full partstree only the children for the specific DU)
- !!! ~Checks for existing slot / mod relations: if they exist, delete them and create the new ones from VLQ~
    - !!! or user decides against that, corrects their entered values (and when doing loading as well to catch the case where the same module was previously loaded to a different DU or on that DU in a different location)
    - !!! or other case when module shall be loaded into a position that is already occupied by another module
- (~!! Checks for fully loaded DU (or not yet fully loaded)~)
- (~!! Display loaded modules in canvas when doing Detector Assembly (CERN)~)
- (~!! Catch when Layer is not suitable for front/back side DU type: allowed: Layer 0,3 for Front, Layer 1,2 for Back, also check for allowed vessel, allowed quadrant, nicer textwrap for info message~)
- (~! Button to open /viewparts page to get further info~)
- ! Button to close application the nice way
- (~! Appearance mode selection~)
- ! Create standalone application (e.g. use pyinstaller?)
- (~! Set Color of progressbar while it is loading to orange (showing that the process is not finished yet), let user know somehow that the process is still running~)
- ! Port the hybrid / sensor matching stuff over here and let user decide what kind of tool they want to use at the moment

## Visuals
A video showing the main features included with v0.0.1 is available under this [cernbox link](https://cernbox.cern.ch/files/spaces/eos/user/a/anstein/public/for_HGTD/screencast_hgtd-tools_v0p0p1.mov) (protected / atlas-hgtd group access only).

## Installation
This suite is written in python, and a conda environment is recommended. The included yaml file also lists a couple of useful packages assisting with further analysing / interpreting the data and was tested to work in April 2025.

### First time usage / requirements:

1. If not already installed, install miniconda, e.g. via `wget https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh` and then running the .sh script (latest release) with e.g. `bash`. On macOS, the installer is termed slightly differently (`...-MacOSX-x86_64.sh`).
2. Clone the repository, e.g. via `git clone ssh://git@gitlab.cern.ch:7999/anstein/hgtd-tools.git` (here: using ssh key).
3. Depending on how conda was installed, it might require opening a new shell and / or sourcing the `~/.bashrc`.
5. Install the environment using the given yaml file: `cd hgtd-tools; conda env create -f env-312.yml` (you can find it in the main directory).

If you don't like conda (☹️ how? 🤨) or you want to minimize the packages to be installed, make sure to run the tools with a recent python3 environment containing `customtkinter`, `requests`, which can be installed with `pip`. Other used packages of hgtd-tools are already part of the regular python3 lib.

## Usage

To open the main window with GUI, execute the following:

```shell
python main.py
```

## Acknowledgements
Thanks to an unknown reddit user who gave me hope when the PyQt6 installation wouldn't want to work with my setup / machine. This [link](https://www.reddit.com/r/Tkinter/comments/snrb1f/comment/hw4bylf/?utm_source=share&utm_medium=web3x&utm_name=web3xcss&utm_term=1&utm_content=share_button) brought me to [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) and the GUI is built on top of the tutorial.
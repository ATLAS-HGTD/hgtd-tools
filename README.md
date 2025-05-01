<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="./windowIcon.png">
    <img src="./windowIcon.png" width=240>
  </picture>
</p>

<div align="center">
    
![Static Badge](https://img.shields.io/badge/python-3.12-blue)

</div>

## Description
These tools interact with the HGTD Production Database for the HGTD Phase-II Upgrade of the ATLAS Experiment at CERN.

## Visuals
A video showing the main features included with v0.0.1 is available under this [cernbox link](https://cernbox.cern.ch/files/spaces/eos/user/a/anstein/public/for_HGTD/screencast_hgtd-tools_v0p0p1.mov) (protected / atlas-hgtd group access only).

## Installation
This suite is written in python, and a conda environment is recommended.

### First time usage / requirements:

1. If not already installed, install miniconda, e.g. via `wget https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh` and then running the .sh script (latest release).
2. Clone the repository, e.g. via `git clone ssh://git@gitlab.cern.ch:7999/anstein/hgtd-tools.git` (using ssh key).
3. Install the environment using the given yaml file: `cd hgtd-tools; conda env create -f env-312.yml` (you can find it in the main directory).

## Usage

To open the main window with GUI, execute the following:

```shell
python main.py
```

## Acknowledgements
Thanks to an unknown reddit user who gave me hope when the PyQt6 installation wouldn't want to work with my setup / machine. This [link](https://www.reddit.com/r/Tkinter/comments/snrb1f/comment/hw4bylf/?utm_source=share&utm_medium=web3x&utm_name=web3xcss&utm_term=1&utm_content=share_button) brought me to [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) and the GUI is built on top of the tutorial.
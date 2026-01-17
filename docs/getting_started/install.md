# Install

This suite is written in python, and a conda environment is recommended. The included yaml file(s) also lists a couple of useful packages assisting with further analysing / interpreting the data and was last tested to work in November 2025.

## First time usage / requirements (recommended way)

This section will show you how to install all requirements to use `hgtd-tools`, including its GUI component, on your device. This route works via getting the code from gitlab, preferably as a git repo that you can update as we develop new features, and installing the python environment via conda.

With the help of our growing user base, we can announce that the tools have been tested on the following platforms:

??? success "Linux"

    1. (If not already installed): install miniconda, e.g. via `wget https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh` and then running the .sh script (latest release) with e.g. `bash`.
    2. Getting the code: clone the repository, e.g. via `git clone ssh://git@gitlab.cern.ch:7999/anstein/hgtd-tools.git` (here: using ssh key). This is the recommended way to always stay up-to-date. You can also choose to download a specific release version, the [latest release is on the top](https://gitlab.cern.ch/anstein/hgtd-tools/-/releases){target="_blank"}.
    3. Depending on how conda was installed (institute & shell specific), it might require opening a new shell and / or sourcing the `~/.bashrc`.
    4. Install the environment using the given yaml file: `cd hgtd-tools; conda env create -f env-312-minimalLinux.yml` (you can find it in the main directory). You may want to test the successful install of the environment with `conda activate hgtd`.
    5. Get the api secret from [cernbox](https://cernbox.cern.ch/files/spaces/eos/user/a/anstein/config_api){target="_blank"} and download the file in the main directory of hgtd-tools. This file is shared with the users-egroup only! Do not distribute it anywhere. If you cannot access the file, you are not in the egroup.

??? success "MacOS"

    ??? info "Not using homebrew"
        1. (If not already installed): install miniconda, e.g. via `wget https://repo.continuum.io/miniconda/Miniconda3-latest-MacOSX-arm64.sh` and then running the .sh script (latest release) with e.g. `bash`. Full instructions for silent install: [see conda docs](https://docs.conda.io/projects/conda/en/stable/user-guide/install/macos.html#installing-in-silent-mode){target="_blank"}. If `wget` does not work for you, download the latest version from here: [conda repo](https://repo.anaconda.com/miniconda/){target="_blank"}. Hint: if you do not want to include the base environment every time you start a new shell, there are ways to disable this behavior: [github gist with instructions](https://gist.github.com/duonghuuphuc/836d99200390b6179ec51e3c50ce18b3){target="_blank"}.
        2. Getting the code: clone the repository, e.g. via `git clone ssh://git@gitlab.cern.ch:7999/anstein/hgtd-tools.git` (here: using ssh key). This is the recommended way to always stay up-to-date. You can also choose to download a specific release version, the [latest release is on the top](https://gitlab.cern.ch/anstein/hgtd-tools/-/releases){target="_blank"}.
        3. Install the environment using the given yaml file: `cd hgtd-tools; conda env create -f env-312.yml` (you can find it in the main directory). You may want to test the successful install of the environment with `conda activate hgtd`.
        4. Get the api secret from [cernbox](https://cernbox.cern.ch/files/spaces/eos/user/a/anstein/config_api){target="_blank"} and download the file in the main directory of hgtd-tools. This file is shared with the users-egroup only! Do not distribute it anywhere. If you cannot access the file, you are not in the egroup.


    ??? info "If you are using homebrew"
        1. Install python with the relevant tk graphics `brew install python-tk`
        2. Create an empty virtual environment with the name hgtd `python3 -m venv hgtd`
        3. Activate the so far empty environment `source hgtd/bin/activate`
        4. Install the necessary packages into this environment `pip3 install -r ./requirements.txt`
        5. Getting the code: clone the repository, e.g. via `git clone ssh://git@gitlab.cern.ch:7999/anstein/hgtd-tools.git` (here: using ssh key). This is the recommended way to always stay up-to-date. You can also choose to download a specific release version, the [latest release is on the top](https://gitlab.cern.ch/anstein/hgtd-tools/-/releases){target="_blank"}.
        6. Move into the project directory `cd hgtd-tools` and get the api secret from [cernbox](https://cernbox.cern.ch/files/spaces/eos/user/a/anstein/config_api){target="_blank"} (download the file in the main directory of hgtd-tools). This file is shared with the users-egroup only! Do not distribute it anywhere. If you cannot access the file, you are not in the egroup.

??? success "Windows"
    1. (If not already installed): install miniconda: go to [anaconda docs](https://www.anaconda.com/docs/getting-started/miniconda/install#windows-command-prompt){target="_blank"} and perform (silent) install of miniconda, via command prompt as described there.
    2. Getting the code: if you don't have a git client on your PC, just download and unzip the repository (click the blue Code button -> Download source code -> zip); if you do have a git client, `git clone ssh://git@gitlab.cern.ch:7999/anstein/hgtd-tools.git` (here: using ssh key). This is the recommended way to always stay up-to-date. You can also choose to download a specific release version, the [latest release is on the top](https://gitlab.cern.ch/anstein/hgtd-tools/-/releases){target="_blank"}.
    3. Installing the environment: open Anaconda Prompt, navigate (`cd`) into the dir where you unzipped the repository, `conda env create -f env-312.yml`. You may want to test the successful install of the environment with `conda activate hgtd`.
    4. Get the api secret from [cernbox](https://cernbox.cern.ch/files/spaces/eos/user/a/anstein/config_api){target="_blank"} and download the file in the main directory of hgtd-tools. This file is shared with the users-egroup only! Do not distribute it anywhere. If you cannot access the file, you are not in the egroup.

If there are no other instructions, this documentation assumes you can successfully activate the `hgtd` environment and you run each python script from your shell. Check the [quickstart instructions](../index.md#quickstart) to learn about running the tools.

## Alternative install without conda

If you don't like conda (☹️ how? 🤨) or you want to minimize the packages to be installed (i.e. without those packages that are helpful for code development and building these docs), make sure to run the tools with a recent python (e.g. here: 3.12) environment containing `customtkinter`, `requests`, which can be installed with `pip`. Other used packages of hgtd-tools are already part of the regular python3 lib. Only the provided yml files shipped with the repo are tested to stay compatible though.

We also include a `requirements.txt` file for convenience (this is also used in the MacOS Brew install guide above with `pip3`).

If you only want to use `hgtd-tools` for its API client without the GUI, `pip install requests` will be enough (see [FADAPro docs on `DB_interface.py`](https://hgtd-fadapro.docs.cern.ch/commandlist/#upload-to-database){target="_blank"}).

## Stable releases instead of pulling from master branch

If you want a stable release, possibly lacking the latest features from the `master` branch, you can always [download release artifacts](https://gitlab.cern.ch/anstein/hgtd-tools/-/releases){target="_blank"}. To update, you would need to get a newer release, or go via the `git clone` route as recommended above.

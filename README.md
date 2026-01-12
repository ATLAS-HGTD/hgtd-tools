<div align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="./windowIcon.png">
    <img src="./windowIcon.png" width=240>
  </picture>
</div>

<div align="center">

![Static Badge](https://img.shields.io/badge/python-3.12-blue) [![Release](https://gitlab.cern.ch/anstein/hgtd-tools/-/badges/release.svg)](https://gitlab.cern.ch/anstein/hgtd-tools/-/releases) [![Pipeline](https://gitlab.cern.ch/anstein/hgtd-tools/badges/master/pipeline.svg)](https://gitlab.cern.ch/anstein/hgtd-tools/-/commits/master) [![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit) [![Static Badge](https://img.shields.io/badge/view-nightly--reports-blue)](https://hgtd-tools-reports.web.cern.ch/) [![Static Badge](https://img.shields.io/badge/read-documentation-blue)](https://hgtd-database.docs.cern.ch/) <br>

![Static Badge](https://img.shields.io/badge/tested_on-Linux_|_MacOS_|_Windows-green)
</div>

⭐️ You can help with testing and improving the tools for more platforms! ⭐️

[[_TOC_]]

## 1. Description
These tools interact with the HGTD Production Database for the HGTD Phase-II Upgrade of the ATLAS Experiment at CERN.

### 1.1 Features
- API (GET / POST / DELETE)
  - in GUI with dynamic progress bar to see API request status
  - efficient lookup of information in local files (e.g. static Slot table) and fetching of dynamic information via ProdDB API
  - allows standalone usage of API client (used e.g. in FADAPro)
- GUI (Linux / Mac / Windows)
  - clickable canvas to get local coordinates easily, conversion to global coordinates done internally where needed
  - buttons to inspect affected parts
  - GUI Modes
    - Module Assembly (MODULE -> MODULE FLEX, MODULE -> HYBRIDs on HV-side / LV-side)
    - Module Loading (DU -> MODULE)
    - Detector Assembly (CERN): DU (DETECTOR -> DU & multiple SLOT -> MODULE)
    - Detector Assembly (CERN): PEB (DETECTOR -> PEB)
    - Detector Assembly (CERN): FT (SLOT -> FT; includes global to local coordinate conversion via Slot table)
  - Logic
    - new relations can overwrite old ones, if user agrees to do so (implementing replacement of existing relations)
      - for Module Assembly, the above also takes care of two hybrids being allowed per module, separating the side
    - user can not load / assemble parts that are not allowed to take that spot (implementing constraints for already used positions, and parts not matching the target position by type)
    - if operation requires subsequent operations (e.g. connecting modules to slots when placing a DU on the detector), perform those subsequent operations in one go, for FT this involves connecting to Slot, Module, Detector Unit and PEB in one go
    - query selection before choosing parent / child from full list (e.g. DU type, module manufacturer, child not yet connected or all possible children)
- Additional scripts / automation
  - Serial Number reservation for module assembly
  - Reporting
    - automation with Gitlab CI, using the hgtdbot account
    - runner script producing overviews / reports
  - Flex Tail upload provided by `upload_FlexTail_measurements.py`

### 1.2 Open points requiring implementation
New features, bugs, compatibility improvements and other items are collected with the [Issues](https://gitlab.cern.ch/anstein/hgtd-tools/-/issues)

Some of them are also bound to [Milestones](https://gitlab.cern.ch/anstein/hgtd-tools/-/milestones)

## 2. Installation
This suite is written in python, and a conda environment is recommended. The included yaml file also lists a couple of useful packages assisting with further analysing / interpreting the data and was last tested to work in November 2025.

### 2.1 First time usage / requirements:

#### 2.1.A Linux:
1. (If not already installed): install miniconda, e.g. via `wget https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh` and then running the .sh script (latest release) with e.g. `bash`.
2. Getting the code: clone the repository, e.g. via `git clone ssh://git@gitlab.cern.ch:7999/anstein/hgtd-tools.git` (here: using ssh key). This is the recommended way to always stay up-to-date. You can also choose to download a specific release version, the [latest release is on the top](https://gitlab.cern.ch/anstein/hgtd-tools/-/releases).
3. Depending on how conda was installed (institute & shell specific), it might require opening a new shell and / or sourcing the `~/.bashrc`.
4. Install the environment using the given yaml file: `cd hgtd-tools; conda env create -f env-312-minimalLinux.yml` (you can find it in the main directory).
5. Get the api secret from [cernbox](https://cernbox.cern.ch/files/spaces/eos/user/a/anstein/config_api) and download the file in the main directory of hgtd-tools. This file is shared with the users-egroup only! Do not distribute it anywhere. If you cannot access the file, you are not in the egroup.

#### 2.1.B MacOS:
##### 2.1.B.1 Not using homebrew
1. (If not already installed): install miniconda, e.g. via `wget https://repo.continuum.io/miniconda/Miniconda3-latest-MacOSX-arm64.sh` and then running the .sh script (latest release) with e.g. `bash`. Full instructions for silent install: https://docs.conda.io/projects/conda/en/stable/user-guide/install/macos.html#installing-in-silent-mode. If `wget` does not work for you, download the latest version from here: https://repo.anaconda.com/miniconda/ Hint: if you do not want to include the base environment every time you start a new shell, there are ways to disable this behavior: https://gist.github.com/duonghuuphuc/836d99200390b6179ec51e3c50ce18b3
2. Getting the code: clone the repository, e.g. via `git clone ssh://git@gitlab.cern.ch:7999/anstein/hgtd-tools.git` (here: using ssh key). This is the recommended way to always stay up-to-date. You can also choose to download a specific release version, the [latest release is on the top](https://gitlab.cern.ch/anstein/hgtd-tools/-/releases).
3. Install the environment using the given yaml file: `cd hgtd-tools; conda env create -f env-312.yml` (you can find it in the main directory).
4. Get the api secret from [cernbox](https://cernbox.cern.ch/files/spaces/eos/user/a/anstein/config_api) and download the file in the main directory of hgtd-tools. This file is shared with the users-egroup only! Do not distribute it anywhere. If you cannot access the file, you are not in the egroup.

##### 2.1.B.2 If you are using homebrew
1. Install python with the relevant tk graphics `brew install python-tk`
2. Create an empty virtual environment with the name hgtd `python3 -m venv hgtd`
3. Activate the so far empty environment `source hgtd/bin/activate`
4. Install the necessary packages into this environment `pip3 install -r ./requirements.txt`
5. Getting the code: clone the repository, e.g. via `git clone ssh://git@gitlab.cern.ch:7999/anstein/hgtd-tools.git` (here: using ssh key). This is the recommended way to always stay up-to-date. You can also choose to download a specific release version, the [latest release is on the top](https://gitlab.cern.ch/anstein/hgtd-tools/-/releases).
6. Move into the project directory `cd hgtd-tools` and get the api secret from [cernbox](https://cernbox.cern.ch/files/spaces/eos/user/a/anstein/config_api) (download the file in the main directory of hgtd-tools). This file is shared with the users-egroup only! Do not distribute it anywhere. If you cannot access the file, you are not in the egroup.

#### 2.1.C Windows:
1. (If not already installed): install miniconda: go to https://www.anaconda.com/docs/getting-started/miniconda/install#windows-command-prompt and perform (silent) install of miniconda, via command prompt as described there.
2. Getting the code: if you don't have a git client on your PC, just download and unzip the repository (click the blue Code button -> Download source code -> zip); if you do have a git client, `git clone ssh://git@gitlab.cern.ch:7999/anstein/hgtd-tools.git` (here: using ssh key). This is the recommended way to always stay up-to-date. You can also choose to download a specific release version, the [latest release is on the top](https://gitlab.cern.ch/anstein/hgtd-tools/-/releases).
3. Installing the environment: open Anaconda Prompt, navigate (`cd`) into the dir where you unzipped the repository, `conda env create -f env-312.yml`.
4. Get the api secret from [cernbox](https://cernbox.cern.ch/files/spaces/eos/user/a/anstein/config_api) and download the file in the main directory of hgtd-tools. This file is shared with the users-egroup only! Do not distribute it anywhere. If you cannot access the file, you are not in the egroup.


If you don't like conda (☹️ how? 🤨) or you want to minimize the packages to be installed, make sure to run the tools with a recent python3 environment containing `customtkinter`, `requests`, which can be installed with `pip`. Other used packages of hgtd-tools are already part of the regular python3 lib. Only the provided yml files are tested to stay compatible though. If you only want to use hgtd-tools for its API client without the GUI, `pip install requests` will be enough (see FADAPro).

### 2.2 Updating your local hgtd-tools if this is not your first time installing:

Make sure you get the most recent version, including new features and bugfixes.

If you opted to get hgtd-tools via `git clone` of the repository, you can go ahead by grabbing the changes from here with commands like the following:
```
git switch master
git fetch origin
git pull origin master
```

If you only downloaded a certain version without any git commands, simply download the [latest version](https://gitlab.cern.ch/anstein/hgtd-tools/-/releases) that replaces your local version.

Note: if you had already cloned and installed all dependencies for hgtd-tools and now want to update your conda-environment, you can do
```
conda env update --file env-312.yml  --prune
```
or
```
conda env update --file env-312-minimalLinux.yml  --prune
```
depending on your system.

## 3. Usage

### 3.1 Using the `SN_reservation.py` script for module assembly

When performing module assembly, you can reserve $N$ serial numbers that are available for your use case. The tool makes sure to create suitable SNs that match your prefix, and fill any potential unused counters (holes) with new SNs for you. The optional `--dryrun` argument can be useful when you just want to know what would be created (as in, this recommends the next free SNs for you, without actually storing those new parts in the DB).

Execute the following from the hgtd-tools directory (using either Anaconda Prompt or your preferred shell with which you installed miniconda):

```shell
conda activate hgtd
python SN_reservation.py --user-name <your-user-name> --site <some-site> --prod <some-prod> --batch <some-batchNr> --n-reserve <how-many-SNs-to-reserve> (--dryrun True)
```

### 3.2 Using the `main.py` GUI for Part-to-Part relations, starting from module assembly

If you have done some connections between multi-relation parts, like module assembly, module loading, detector assembly with DUs, PEBs or Flex Tails, or you want to get assistance on what to pick, use the GUI of hgtd-tools.

To open the main window with GUI, execute the following from the hgtd-tools directory (using either Anaconda Prompt or your preferred shell with which you installed miniconda):

```shell
conda activate hgtd
python main.py
```

Closing the application works like you would expect from other applications, e.g. you'll find a red button to close hgtd-tools, you could quit the application with shortcuts of your operating system (e.g. MacOS: cmd+Q), or interrupting the python program from command line with ctrl+c.

#### 3.2.1 Documentation of typical use cases of the GUI application
We have a new [documentation page](https://hgtd-database.docs.cern.ch/) for the HGTD Production Database, which contains a [section on hgtd-tools](https://hgtd-database.docs.cern.ch/content/user/parts_tree_hgtd-tools/) as well. You will find guides to use the tools over there.


### 3.3 Using the `upload_FlexTail_measurement.py` script for uploading flex tail measurements

After performing all electrical and mechanical measurements of a batch of flex tails, upload the folder containing all measurements to the database. The optional `--dryrun` argument can be useful to test if the upload will succeed or not. For more information on the uploading procedure, please read `FT_upload_instructions.md`.

Execute the following from the hgtd-tools directory:

```shell
conda activate hgtd
python upload_FlexTail_measurement.py --analysis-folder FT_Measurements --user-name myName --meas_location test --meas_start_date YYYY-MM-DD --meas_end_date YYYY-MM-DD --run_type FT_characterisation_test (--dryrun True)
```

## 4. Developer corner
### 4.1 Reusing the included API module
The `api.py` module can be used standalone as well to make API requests to the HGTD Production Database. Note that the included functions also return the response `status_code` and `reason` and handle a variety of possible errors.

The basic types of requests are:

- **GET**: without payload, fetch some specified record/view etc.
- **POST**: sends a payload (dictionary as json, or more involved types like a tar for measurement data, with another dictionary for human-readable requests)
- **DELETE**: without payload, remove some record

Those three variants are implemented as `api.fetch_information`, `api.post_information`, `api.delete_information` handling the endpoint, headers etc. for you so you don't have to worry about anything besides the actual information received, posted or deleted.

#### 4.1.1 REST API HTTP Status Codes 101

Please refer to this overview of the most common status codes and what you can learn from them:

- **Starts with 2**: good news, wohoo! Your request was successful, e.g. retrieving data (200) or creating new data upstream (201).
- **Starts with 4**: you sure what you are doing is correct? Likely a typo or bad payload in your request (400) when the endpoint exists, but it does not like your request, or missing authentication / access token (401). Could also be wrong URL (404) which is similar to dialing a phone number that does not exist ("The number you have dialed is not in service.", but in the web edition).
- **Starts with 5**: server has received your request, but failed to process it internally. Can be an error that is not caught, e.g. the python-portion of our backend had an error while processing (500), not further specified where and what went wrong. Could also be something related to DB / some infrastructure not available or overlaoded (502 / 503), or your request taking too long / timeout (504).

More codes and their explanation are documented for example over at [wikipedia](https://en.wikipedia.org/wiki/List_of_HTTP_status_codes).

#### 4.1.2 Worked out standalone example and the API client in action
Have a look at the notebook `example_API_usage.ipynb` to see the included API module in action. The notebook shows two use cases for user interaction with the DB that can be implemented as part of scripts (as in FADAPro, for example): adding a value for a single attribute (useful for e.g. module metrology) or complete bulk upload of a tar containing various files (useful for e.g. module electrical measurements). For proper authentication, these steps to get started are included as well.

The interface to FADAPro is implemented in the [MR](https://gitlab.cern.ch/atlas-hgtd/Electronics/fadapro/-/merge_requests/9).

In work: interface for flex tail measurement uploads.

### 4.2 Dockerization (discontinued)
A deployment of this app to CERN OKD using docker was attempted, but discontinued because of difficulties getting the graphical part running and deploying the same, while now practically all users are comfortable using the tools standalone on their device. Local docker containers were running well on test platforms (e.g. lxplus with `ssh -XY`), however, due to security measures, buttons that bring you to a special URL in your system's browser were blocked. The instructions for docker development are therefore archived under [development_docs/docker.md](https://gitlab.cern.ch/anstein/hgtd-tools/-/blob/master/development_docs/docker.md?ref_type=heads) and will not be continued.

### 4.3 pre-commit

We use some standard pre-commit hooks (see `.pre-commit-config.yaml`). If you want to setup this helpful tool as well:

```shell
pre-commit install
```

And you can run the hooks on all files by

```shell
pre-commit run --all-files
```

### 4.4 New version policy and process
The procedure for tagging new versions of this software is outlined in [development_docs/procedure_new_release.md](https://gitlab.cern.ch/anstein/hgtd-tools/-/blob/master/development_docs/procedure_new_release.md?ref_type=heads).

## 5. Contributing
For any problems, do not hesitate to ask on [mattermost](https://mattermost.web.cern.ch/atlas/channels/hgtd-production-database) or open an [Issue](https://gitlab.cern.ch/anstein/hgtd-tools/-/issues) after checking the existing issues.

If you are developing features yourself or want to resolve an issue, please [Fork](https://gitlab.cern.ch/anstein/hgtd-tools/-/forks/new) this repository and then submit a [Merge Request](https://gitlab.cern.ch/anstein/hgtd-tools/-/merge_requests/new) to the [master branch](https://gitlab.cern.ch/anstein/hgtd-tools). Add `anstein` as a member of your private fork with at least `Reporter` rights, such that during MR review, your reviewer can see the pipelines in your fork.

We run a set of basic pre-commit checks for your MR, so be prepared to modify the changed files according to the `.gitlab-ci.yaml` pipeline before your MR can be merged. Test your changes locally before pushing (and avoid using unneccessary CI time + core-h), using the instructions outlined in the pre-commit paragraph.

Not every minor commit needs to trigger a CI pipeline, for example clerical changes or something that only affects documentation but no logic. In that case, please adapt your regular commit message as follows to skip the CI for a specific commit:

```bash
git commit -m 'here is my regular commit message [skip ci]'
```

(note the `[skip ci]` flag).

## 6. Acknowledgements
Thanks to an unknown reddit user who gave me hope when the PyQt6 installation wouldn't want to work with my setup / machine. This [link](https://www.reddit.com/r/Tkinter/comments/snrb1f/comment/hw4bylf/?utm_source=share&utm_medium=web3x&utm_name=web3xcss&utm_term=1&utm_content=share_button) brought me to [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) and the GUI is built on top of the tutorial.

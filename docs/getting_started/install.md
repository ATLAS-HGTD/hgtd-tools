# Install

Last update: August 2026

This suite is written in python, and after placing yourself into a virtual environment or conda environment (more on that below), the tools themselves can be installed via `pip install hgtd-tools` (or with optional dependencies, such as `pip install hgtd-tools[gui]`). Presently the optional dependencies are: `[dev,dev-extra,docs,gui]`, you can mix them in any combination).

The package is now published on [PyPI](https://pypi.org/project/hgtd-tools/){target="_blank"}, so installing it **no longer requires cloning the gitlab repository** — cloning is only needed if you want to develop the tools themselves (see the [Developer setup](#developer-setup) section below). Detailed step-by-step instructions differ slightly depending on platform (especially relevant for the GUI part). Linux users should go the install route via conda if they wish to use the GUI, because it depends on `Tk`. The corresponding `env-312-withTk-linux.yml` file is provided in the root of the [gitlab repository](https://gitlab.cern.ch/anstein/hgtd-tools){target="_blank"} — just download it and follow the step-by-step instructions below.

For non-linux users, you can either use the conda environment as shown below, or simply create a venv/conda env, activate it, and `pip install hgtd-tools[gui]` directly.

## First time usage / requirements (recommended way)

This section will show you how to install all requirements to use `hgtd-tools`, including its GUI component, on your device. This route works via creating a Python environment (conda or venv) and installing the package from PyPI.

With the help of our growing user base, we can announce that the tools have been tested on the following platforms:

=== "Linux"

    1. (If not already installed): install miniconda: go to [anaconda docs](https://www.anaconda.com/docs/getting-started/miniconda/install/linux-install#wget){target="_blank"} and follow the instructions there.
    2. Download the conda environment YAML from the root of the [gitlab repository](https://gitlab.cern.ch/anstein/hgtd-tools){target="_blank"}: [`env-312-withTk-linux.yml`](https://gitlab.cern.ch/anstein/hgtd-tools/-/raw/master/env-312-withTk-linux.yml){target="_blank"} (recommended if you want to use the GUI, because it ships Tk) — or `env-312.yml` if you don't need the GUI.
    3. Install the environment: open a Terminal, navigate (`cd`) to the directory where you downloaded the YAML, and run `conda env create -f env-312-withTk-linux.yml`. Activate the environment with `conda activate hgtd`.
    4. Install the package from PyPI: `pip install hgtd-tools[gui]` (or, if you do not need the GUI, `pip install hgtd-tools`).
    5. Get the API secret from [cernbox](https://cernbox.cern.ch/files/spaces/eos/user/a/anstein/config_api){target="_blank"} and place the file in one of these locations:

        - `~/.hgtd_tools/config_api` (recommended), or
        - `./config_api` in the directory from which you'll launch the tools.

        The home location takes precedence if both exist. Restrict the permissions afterwards: `chmod 600 ~/.hgtd_tools/config_api`. This file is shared with the proddb-users-egroup only! Do not distribute it anywhere. If you cannot access the file, you are not in the egroup. An error message will tell you if the file is missing and where to put it in your use case.

=== "MacOS"

    === "Not using homebrew"

        1. (If not already installed): install miniconda: go to [anaconda docs](https://www.anaconda.com/docs/getting-started/miniconda/install/mac-cli-install){target="_blank"} and follow the instructions there. By default, this will activate the `(base)` environment when a new shell is started. The command to tune this behavior to your liking is discussed [in the troubleshooting section of anaconda docs](https://www.anaconda.com/docs/getting-started/miniconda/install/mac-cli-install#set-auto-activate-base-to-true){target="_blank"}.
        2. Download the conda environment YAML from the root of the [gitlab repository](https://gitlab.cern.ch/anstein/hgtd-tools){target="_blank"}: [`env-312.yml`](https://gitlab.cern.ch/anstein/hgtd-tools/-/raw/master/env-312.yml){target="_blank"}.
        3. Install the environment: open a Terminal, navigate (`cd`) to the directory where you downloaded the YAML, and run `conda env create -f env-312.yml`. Activate the environment with `conda activate hgtd`.
        4. Install the package from PyPI: `pip install hgtd-tools[gui]` (or, if you do not need the GUI, `pip install hgtd-tools`).
        5. Get the API secret from [cernbox](https://cernbox.cern.ch/files/spaces/eos/user/a/anstein/config_api){target="_blank"} and place the file in one of these locations:

            - `~/.hgtd_tools/config_api` (recommended), or
            - `./config_api` in the directory from which you'll launch the tools.

            The home location takes precedence if both exist. Restrict the permissions afterwards: `chmod 600 ~/.hgtd_tools/config_api`. This file is shared with the proddb-users-egroup only! Do not distribute it anywhere. If you cannot access the file, you are not in the egroup. An error message will tell you if the file is missing and where to put it in your use case.

    === "If you are using homebrew"

        1. Install python with the relevant tk graphics `brew install python-tk`
        2. Create an empty virtual environment with the name hgtd `python3 -m venv hgtd`
        3. Activate the so far empty environment `source hgtd/bin/activate`
        4. Install the package from PyPI: `pip install hgtd-tools[gui]` (or, if you do not need the GUI, `pip install hgtd-tools`).
        5. Get the API secret from [cernbox](https://cernbox.cern.ch/files/spaces/eos/user/a/anstein/config_api){target="_blank"} and place the file in one of these locations:

            - `~/.hgtd_tools/config_api` (recommended), or
            - `./config_api` in the directory from which you'll launch the tools.

            The home location takes precedence if both exist. Restrict the permissions afterwards: `chmod 600 ~/.hgtd_tools/config_api`. This file is shared with the proddb-users-egroup only! Do not distribute it anywhere. If you cannot access the file, you are not in the egroup. An error message will tell you if the file is missing and where to put it in your use case.

=== "Windows"

    1. (If not already installed): install miniconda: go to [anaconda docs](https://www.anaconda.com/docs/getting-started/miniconda/install/windows-cli-install){target="_blank"} and follow the instructions there.
    2. Download the conda environment YAML from the root of the [gitlab repository](https://gitlab.cern.ch/anstein/hgtd-tools){target="_blank"}: [`env-312.yml`](https://gitlab.cern.ch/anstein/hgtd-tools/-/raw/master/env-312.yml){target="_blank"}.
    3. Install the environment: open Anaconda Prompt, navigate (`cd`) to the directory where you downloaded the YAML, and run `conda env create -f env-312.yml`. Activate the environment with `conda activate hgtd`.
    4. Install the package from PyPI: `pip install hgtd-tools[gui]` (or, if you do not need the GUI, `pip install hgtd-tools`).
    5. Get the API secret from [cernbox](https://cernbox.cern.ch/files/spaces/eos/user/a/anstein/config_api){target="_blank"} and place the file in one of these locations:

        - `%USERPROFILE%\.hgtd_tools\config_api` (recommended), or
        - `.\config_api` in the directory from which you'll launch the tools.

        The home location takes precedence if both exist. This file is shared with the proddb-users-egroup only! Do not distribute it anywhere. If you cannot access the file, you are not in the users egroup. An error message will tell you if the file is missing and where to put it in your use case.

The following documentation pages assume you can successfully activate the `(hgtd)` environment, allowing you to run each script and the GUI from your shell. Check the [quickstart instructions](../index.md#quickstart) to learn about running the tools, or take a deeper look with the individual pages per tool.

## Developer setup

[Fork the repository](https://gitlab.cern.ch/anstein/hgtd-tools/-/forks/new){target="_blank"}, and clone your fork locally. Create a new branch starting from `master` to work on your feature / fix: `git switch -c branch_name`. Activate your virtual environment / conda (whichever system you prefer and need for your platform). A separate environment for local development will allow working on your local changes and keeping a working version alive in another env for production use.

Depending on what features you are developing, you can install optional dependencies. To make sure your install picks up the local changes (editable), use the `-e .` notation for `pip` instead of pulling a fixed version from PyPI directly:

```bash
pip install -e ".[dev,dev-extra,docs,gui]"
```
The example above installs all optional dependencies, but the command depends on what you are working on.

- `dev`: minimum for development, as it installs [`pre-commit`](../development/dev.md#pre-commit). Every commit should be automatically checked with this tool. Additionally, Jupyter Lab is included, allowing you to learn from / with example `.ipynb` notebooks.
- `dev-extra`: the project owner/maintainer's extras, used for building the package and uploading to PyPI.
- `docs`: when you modify the documentation, this allows local serving / building static sites of the docs with Zensical.
- `gui`: every user wishing to open the GUI, not only developers, should add this dependency. It is by default included in the user-facing docs above. In settings where the GUI is not needed (e.g. potentially a headless operation of FADAPro uploads, or when using it for the command-line scripts only), this dependency can also be dropped and the command would just be `pip install hgtd-tools`.

For contributing back to the central repo, the [contributing instructions](../development/dev.md#contributing) apply.

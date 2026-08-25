# Updating hgtd-tools

How to move to a new version of hgtd-tools depends on what you are aiming at doing (just using the tools, or also developing them), and which version you currently have on your system.

## User

Are you working with conda? Or a virtual environment? Activate your environment.

### Only when working with conda
If it is conda, you can update it to the latest dependencies outlined in the [gitlab repository](https://gitlab.cern.ch/anstein/hgtd-tools) by downloading the corresponding `.yml` env file and performing an update of the environment:
```bash
conda env update --file env-312.yml  --prune
```
or
```bash
conda env update --file env-312-withTk-linux.yml  --prune
```
depending on your system.

If this has conflicts that can't be resolved, remove the old environment or create a new one (maybe with a new name, as you prefer):
```bash
conda env create -f <the-right-file-for-your-platform>.yml -n a-new-env-name-if-you-want
```

### As user, install from centrally provided PyPI package
Afterwards, you will need to install the actual package:

```bash
pip install hgtd-tools[gui]
```
(but note that the `[gui]` is optional, you only need it if you want to work with the GUI).

## Developer

You should grab a recent commit from `master`, ideally by updating your fork on GitLab. Locally, you'd do `git fetch` and, for example if your remote fork is named `myfork` in your local git: `git pull myfork master`. If your own fork is named `origin` locally, then `git pull origin master`. Create a new branch from that `git switch -c new_branch_name`.

Are you working with conda? Or a virtual environment? Activate your environment.

### Only when working with conda
If it is conda, you can update it to the latest dependencies outlined in the [gitlab repository](https://gitlab.cern.ch/anstein/hgtd-tools) by selecting the corresponding `.yml` env file and performing an update of the environment:
```bash
conda env update --file env-312.yml  --prune
```
or
```bash
conda env update --file env-312-withTk-linux.yml  --prune
```
depending on your system.

If this has conflicts that can't be resolved, remove the old environment or create a new one (maybe with a new name, as you prefer):
```bash
conda env create -f <the-right-file-for-your-platform>.yml -n a-new-env-name-if-you-want
```

### As developer, install from local source
Afterwards, you will need to install the actual package locally (with the source you checked out via git above):

```bash
pip install -e ".[dev,dev-extra,docs,gui]"
```

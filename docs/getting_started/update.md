# Updating hgtd-tools

Updating your local hgtd-tools if this is not your first time installing can be done either with git commands or by downloading a more recent named release.

## Latest master
Make sure you get the most recent version, including new features and bugfixes.

If you opted to get hgtd-tools via `git clone` of the repository, you can go ahead by grabbing the changes from here with commands like the following:
```
git switch master
git fetch origin
git pull origin master
```

## Recent release
If you only downloaded a certain version without any git commands, simply download the [latest version](https://gitlab.cern.ch/anstein/hgtd-tools/-/releases) that replaces your local version.

## Updating your python environment
Note: if you had already cloned and installed all dependencies for hgtd-tools and now want to update your conda-environment (because the env file itself got an update in the repo), you can do
```
conda env update --file env-312.yml  --prune
```
or
```
conda env update --file env-312-minimalLinux.yml  --prune
```
depending on your system.

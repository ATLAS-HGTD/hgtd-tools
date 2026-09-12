# Updating hgtd-tools

How to move to a new version of hgtd-tools depends on what you are aiming at doing (just using the tools, or also developing them; standalone or with FADAPro), and which version you currently have on your system.

## Python environment for users of HGTD Tools

Pick your specific setup from which you are upgrading:

=== "Standalone HGTD Tools"

    === "Currently installed version: 2.0.0 or older"

        === "Conda"

            1. Remove the old environment to start fresh.

                a. Make sure your (old) conda env is not active, if it is active, deactivate it: `conda deactivate`.

                b. Delete the old conda environment, e.g. if it was called `hgtd` i.e. appears in your command-line as `(hgtd)`, then do: `conda remove --name hgtd --all`.

            2. Continue with the regular [install guidelines](./install.md), as if it was your first time installing the package. You don't need to come back to this page afterwards.

        === "venv"

            1. Users of a regular standalone venv (also applies to brew users on Mac) do `source hgtd/bin/activate`, or however you named your venv (`source yourCustomEnvName/bin/activate`).
            2. Afterwards, you will need to upgrade the actual package, centrally provided via PyPI, with the recommended optional dependency of `[gui]` to allow operations with the GUI:

                ```bash
                pip install --upgrade "hgtd-tools[gui]"
                ```

    === "Already using at least version 3.0.0"

        === "Conda"

            Activate your environment. Conda users do so with `conda activate hgtd`, if your environment (check your terminal) is `(hgtd)` as recommended in the install guidelines.

        === "venv"

            Activate your environment. Users of a regular standalone venv (also applies to brew users on Mac) do `source hgtd/bin/activate`, or however your named your venv (`source yourCustomEnvName/bin/activate`).

        Afterwards, you will need to upgrade the actual package, centrally provided via PyPI, with the recommended optional dependency of `[gui]` to allow operations with the GUI:

        ```bash
        pip install --upgrade "hgtd-tools[gui]"
        ```

=== "Together with FADAPro"

    If you are using hgtd-tools in [conjunction with `FADAPro`](https://hgtd-fadapro.docs.cern.ch/installation/requirements/){target="_blank"}, simply activate your data analysis venv: `source /home/$USER/ModuleAssembly/python3_env/analysis/bin/activate`.

    Afterwards, you will need to upgrade the actual package, centrally provided via PyPI, without optional dependencies because all that's needed is the API client interface to the ProdDB:

    ```bash
    pip install --upgrade hgtd-tools
    ```


## Developer

### Updating your (forked) repository

You should grab a recent commit from `master`, ideally by updating your fork on GitLab. Locally, you'd do `git fetch` and, for example if your remote fork is named `myfork` in your local git: `git pull myfork master`. If your own fork is named `origin` locally, then `git pull origin master`. Create a new branch from that `git switch -c my_new_branch_name`.

### Python environment for developers

The same instructions as for users apply, with the addition that you do install any modified python modules from the local source in editable mode. Head into your own local clone of the project (`cd hgtd-tools`) and then do:

```bash
pip install -e ".[dev,dev-extra,docs,gui]" --upgrade
```

This will upgrade all available optional dependencies (also those for development, documentation building and of course the GUI) and allow you to work on the code yourself.

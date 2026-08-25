# Procedure for new release

1. commit with planned version already embedded in `pyproject.toml`
2. push to master
3. prepare the package for pypi, for reference, this is an example for a pre-release on testpypi:
```bash
rm -drf dist
python -m build
tar -tzf dist/hgtd_tools-3.0.0rc1.tar.gz
unzip -l dist/hgtd_tools-3.0.0rc1-py3-none-any.whl
twine upload --repository testpypi dist/*
```
4. test the new package via (again, using testpypi as a reference inside active env):
```bash
pip install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple "hgtd-tools[dev,gui]==3.0.0rc1"
```
5. tag the new version (at vX.Y.Z)
6. push tag
7. ON GITLAB: create new release X.Y.Z from tag vX.Y.Z
8. update version endpoint `hgtd-tools-version` on cernbox with content X.Y.Z [https://cernbox.cern.ch/text-editor/eos/user/a/anstein/hgtd-tools-version](https://cernbox.cern.ch/text-editor/eos/user/a/anstein/hgtd-tools-version){target="_blank"}
9. submit MR to FADAPro to update the submodule or dependency as a pip package (if anything except GUI, i.e. the API interface is affected)
10. email to hgtd-tools-users-announce e-group with the changelog / release notes (also announce what the automatic version checker via CLI will recommend as latest version)

## Ongoing and closed release cycles
v2.0.0: Pre-Production

v1.Y.Z: First release cycle for actual users, part of the ProdDB tutorial

v0.Y.Z: early R&D of the tools

## Plan
roughly one new planned release X.Y each month, patches in between

v3.0.0: Package refactor

v3.1.0: Production

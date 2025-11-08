# Procedure for new release

1. commit with planned version already embedded in `main.py` and in `README.md` (note: no more hardcoding in README necessary)
2. push to master
3. tag the new version (at vX.Y.Z)
4. push tag
5. ON GITLAB: create new release X.Y.Z from tag vX.Y.Z
6. update version endpoint `hgtd-tools-version` on cernbox with content X.Y.Z https://cernbox.cern.ch/text-editor/eos/user/a/anstein/hgtd-tools-version
7. submit MR to FADAPro to update the submodule
8. email to users e-group and message on mattermost users channel with the changelog / release notes

## Ongoing and closed
v1.Y.Z: First release cycle for actual users, part of the ProdDB tutorial
v0.Y.Z: early R&D of the tools

## Plan
roughly one new planned release X.Y each month, patches in between
v2.0.0: Pre-Production
v3.0.0: Production

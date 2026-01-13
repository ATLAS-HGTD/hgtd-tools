# Docker (deprecated)

All docker support for hgtd-tools deprecated on Dec 20th, 2025, in favor of user's python environments.

The following is kept only for archival purposes. The last version containing a Dockerfile is v1.8.1, up to commit 902e9cb9c8f7bdb3aed780c13201041f1db9d246.

---

There are two relevant registry links, for which a login is needed:

first one needs a PAT from gitlab with the right to upload to the registry:
```
docker login gitlab-registry.cern.ch
```
or second one, harbor (see instructions [in ATLAS Software docs](https://atlassoftwaredocs.web.cern.ch/analysis-software/ASWTutorial/softwareEssentials/building_containers/){target="_blank"}). The secret token can be found from top right click user profile and serves as the password when loggin in:
```
docker login registry.cern.ch
```

The second option is used to deploy to the common registry for the whole hgtddb project.


#### X.2.1 Scripts to build / tag / deploy / run container

Note that all commands involving testing the actual GUI from a remote require an X-server, e.g. start a `ssh -XY` connection from inside XQuartz.

You need Docker installed on your device, e.g. Docker Desktop running in the background.

The `Dockerfile` (or `_lxplus_Dockerfile`) are setup to directly run to the entrypoint that starts the `main.py` with all dependencies already setup.

On Mac: use `bash docker-build_run_on_Mac.sh` if you want to build a new container from the source and run it locally for testing. If you are happy with that, do `bash docker-build_push_for_amd64.sh` to build for the platform that is present at CERN (lxplus, pod -> amd64). You can also run a container on Mac without building a new one, by doing `bash docker-run_on_Mac.sh`.

On linux / lxplus: there is another Dockerfile that pulls the base image from another registry (due to limited number of pulls from the same unauthenticated IP address). You can run a container with an already existing image `bash docker-run_on_lxplus.sh` (see this [source](https://gist.github.com/Moosems/138cfea6fc4e1967e4eae52bd96618ff){target="_blank"}) and to build a new image do `bash docker-build_run_on_linux.sh` (does not work yet on lxplus, or you need special rights / uid / gid to perform apt-get install commands).


#### X.2.2 Useful commands to do the build / tag / push / run manually

Build and push a `latest` image to gitlab:
```
docker login gitlab-registry.cern.ch
docker build -t gitlab-registry.cern.ch/anstein/hgtd-tools .
docker push gitlab-registry.cern.ch/anstein/hgtd-tools
```

Use an existing image (see above), tag it with version and push these new ones to harbor:
```
docker login registry.cern.ch

docker tag gitlab-registry.cern.ch/anstein/hgtd-tools registry.cern.ch/hgtd/hgtd-tools:latest
docker tag gitlab-registry.cern.ch/anstein/hgtd-tools registry.cern.ch/hgtd/hgtd-tools:1.4.2

docker push registry.cern.ch/hgtd/hgtd-tools:latest
docker push registry.cern.ch/hgtd/hgtd-tools:1.4.2

docker image tag registry.cern.ch/hgtd/hgtd-tools:x86_64_1.4.2 registry.cern.ch/hgtd/hgtd-tools:latest
docker push registry.cern.ch/hgtd/hgtd-tools:latest
docker push registry.cern.ch/hgtd/hgtd-tools:x86_64_1.4.2

```

# Which registry to push to. First version pushes to gitlab-registry, the second one to harbor
#export reg="gitlab-"
export reg=""
# Similar to the above, gitlab has anstein as owner, while the harbor is under hgtd
#export userproject="anstein"
export userproject="hgtd"

# Find the latest tagged software version in the git repo and only proceed if this is an actual tagged version (not just the regular master branch)
branch=`git describe --all`
export tools_branch=${branch#*/}

if [ "${tools_branch}" = "master" ] ; then
  echo "You try to build a docker image for hgtd-tools/${tools_branch}, which is not a tagged version, aborting process."
else
  echo "You are building the docker image for hgtd-tools/${tools_branch}"

  # Compare with eventual previously pushed docker_tag
  docker_tag_file="docker_tag.txt"
  docker_tag_change=false
  if [ -f ${docker_tag_file} ]; then
    previous_tag=`cat ${docker_tag_file}`
    if [[ "${previous_tag}" == *"${tools_branch}"* ]]; then
      echo "You already use hgtd-tools docker_tag ${previous_tag}. This will not be built again, no push to registry, aborting process."
    else
      echo "The current hgtd-tools docker_tag ${tools_branch} is not the same as the last docker_tag ${previous_tag}. Proceeding with docker command."
      docker_tag_change=true
    fi
  else
    echo "The docker_tag.txt file is missing. Probably this is your first build / push. Proceeding with docker command."
    docker_tag_change=true
  fi

  # Build and push the image for CERN registry (harbor), push requires login
  if [ "${docker_tag_change}" = true ] ; then
    docker buildx build --push --platform linux/amd64 -t ${reg}registry.cern.ch/${userproject}/hgtd-tools:x86_64_${tools_branch} \
    -t ${reg}registry.cern.ch/${userproject}/hgtd-tools:latest .
    if [ $? -eq 0 ]; then
      echo "${tools_branch}" > docker_tag.txt
    fi
  fi
fi

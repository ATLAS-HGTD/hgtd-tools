# Find the latest tagged software version in the git repo
branch=`git describe --all`
export tools_branch=${branch#*/}
export tools_branch="1.4.3"
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
  docker buildx build --push --platform linux/amd64 -t registry.cern.ch/hgtd/hgtd-tools:x86_64_${tools_branch} \
  -t registry.cern.ch/hgtd/hgtd-tools:latest .

  # only if the above was successful (ToDo)
  echo "${tools_branch}" > version.txt
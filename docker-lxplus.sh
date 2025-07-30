#!/bin/bash

# Build the image
#docker build -t hgtd_container .

# Get IP address of the host
IP=$(hostname -I | awk '{print $1}')

# Print IP address
echo "IP: $IP"

# Allow connections to X server
xhost +local:docker

# Run the container
docker run -e DISPLAY=$DISPLAY \
           -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
           -v $HOME/.Xauthority:/root/.Xauthority:rw \
           --net=host \
           --rm -it registry.cern.ch/hgtd/hgtd-tools@sha256:1eda1156887119601b9ab79ed1e0ce38c50c21eeffcb5994c2a37f72db47204d

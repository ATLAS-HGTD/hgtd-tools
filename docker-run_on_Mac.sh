# Run a docker container from the registry on MacOS

# Get IP address of Mac
IP=$(/usr/sbin/ipconfig getifaddr en0)

# Print IP address
echo "IP: $IP"

# Allow connections through XQuartz
/opt/X11/bin/xhost + "$IP"

# Run the container (this one was build with Mac, platform linux/arm64/v8)
docker run -it -e DISPLAY=${IP}:0 --rm --network="host" registry.cern.ch/hgtd/hgtd-tools@sha256:1eda1156887119601b9ab79ed1e0ce38c50c21eeffcb5994c2a37f72db47204d

# Build the image
docker build -t hgtd_container .

# Get IP address of Mac
IP=$(/usr/sbin/ipconfig getifaddr en0)

# Print IP address
echo "IP: $IP"

# Allow connections through XQuartz
/opt/X11/bin/xhost + "$IP"

# Run the container
docker run -it -e DISPLAY=${IP}:0 --rm --network="host" hgtd_container
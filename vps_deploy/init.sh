!/bin/bash

# Ensure server IP is passed as an argument
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 server_ip"
    exit 1
fi

SERVER_IP=$1

# Run the remote script via SSH
ssh root@$SERVER_IP 'bash -s' < remote-script.sh

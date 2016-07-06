#!/usr/bin/env bash

set -eu

IMAGE="cgbudocker.us.oracle.com:7878/leo/stacktools:latest"

if [[ $# != 2 ]]; then
    echo "Usage: wrapper.sh OPENRC_PATH SSHKEY_PATH"
    exit 1
fi

OPENRC=$1
SSHKEY=$2

docker pull $IMAGE
docker run --name stacktools --hostname stacktools --rm -it -v $(readlink -e $OPENRC):/root/openrc -v $(readlink -e $SSHKEY):/root/sshkey.pem $IMAGE bash -c "source /root/openrc && /bin/bash"

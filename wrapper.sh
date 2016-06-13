#!/usr/bin/env bash

set -eu

IMAGE="commscloud_stacktools"

if [[ $# != 2 ]]; then
    echo "Usage: wrapper.sh OPENRC_PATH SSHKEY_PATH"
    exit 1
fi

OPENRC=$1
SSHKEY=$2

docker run --rm -it -v $OPENRC:/root/openrc -v $SSHKEY:/root/sshkey.pem $IMAGE bash -c "source /root/openrc && /bin/bash"

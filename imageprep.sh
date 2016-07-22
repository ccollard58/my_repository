#!/usr/bin/env bash

set -eu

if [[ $# != 2 ]]; then
    echo "Usage: imageprep.sh PATH_TO_OVA IMAGE_NAME"
    exit 1
fi

if ! [[ "$1" =~ \.(ova|ovf)$ ]]
 then
  echo "Invalid file argument - received $1"
  echo "File should be in .ova or .ovf format"
  exit 1
fi

if ! [ -f $1 ]
  then
    echo "$1 does not exist."
    exit 1
fi

tar -xvf $1 > /dev/null 2>&1
vmdkname="$(ls | grep -Po '.+(?=\.vmdk)').vmdk"

qemu-img convert -f vmdk -O qcow2 $vmdkname $2

# sudo chroot $TEMP /bin/bash -c "/sbin/chkconfig cloud-init-local on; /sbin/chkconfig cloud-init on; /sbin/chkconfig cloud-config on; /sbin/chkconfig cloud-final on"
guestfish -a $2 -i <<EOF
sh "chkconfig cloud-init on"
sh "chkconfig cloud-init-local on"
sh "chkconfig cloud-config on"
sh "chkconfig cloud-final on"
EOF

openstack image create --disk-format qcow2 --file $2 $2

rm -f $2

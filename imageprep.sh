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

sudo tar -xvf $1 > /dev/null 2>&1
vmdkname="$(ls | grep -Po '.+(?=\.vmdk)').vmdk"

sudo qemu-img convert -f vmdk -O qcow2 $vmdkname $2
sudo modprobe -r nbd
sudo modprobe nbd max_part=8

for nbd_device in /sys/class/block/nbd*; do
    size=`cat $nbd_device/size`
    if [ "$size" -eq 0 ] ; then
        device_number=$(basename $nbd_device | grep -Po "[0-9]+$")
        sudo qemu-nbd --connect=/dev/nbd$device_number $2
        sudo partx -a /dev/nbd$device_number
        break
    fi
done

TEMP=$(mktemp -d)

sudo pvscan --cache
sudo vgscan
sudo vgchange -ay vgroot
sudo mount /dev/vgroot/plat_root $TEMP


sudo chroot $TEMP /bin/bash -c "/sbin/chkconfig cloud-init-local on; /sbin/chkconfig cloud-init on; /sbin/chkconfig cloud-config on; /sbin/chkconfig cloud-final on"

sudo umount $TEMP
sudo rm -r $TEMP

sudo vgchange -an vgroot
sudo qemu-nbd -d /dev/nbd$device_number
sudo pvscan --cache

openstack image create --disk-format qcow2 --file $2 $2

rm -f $2

#!/bin/bash

set -eu

if ! [[ "$1" =~ \.(ova|ovf)$ ]]
 then
  echo "Invalid file argument - received $1"
  echo "File should be in .ova or .ovf format"
  exit 1
fi

if [ -z "$2" ]
 then
   echo "No name for image supplied"
   echo "Please supply an image name"
   exit 1
fi

sudo tar -zxvf $1 > /dev/null 2>&1
vmdkname="$(ls | grep -Po '.+(?=\.vmdk)').vmdk"

sudo qemu-img convert -f vmdk -O qcow2 $vmdkname $2
sudo modprobe -r nbd
sudo modprobe nbd max_part=8

for nbd_device in /sys/class/block/nbd*; do
    $size=`cat $nbd_device/size`
    if [ "$size" -eq 0 ] ; then
        $device_number = $(basename $x | grep -Po "[0-9]+$")
        sudo qemu-nbd --connect=/dev/nbd$device_number $2
        break
    fi

done

TEMP = $(mktemp -d)

sudo pvscan --cache
sudo vgscan
sudo vgchange -ay vgroot
sudo mount /dev/vgroot/plat_root $TEMP


sudo chroot $TEMP /bin/bash -c "/sbin/chkconfig cloud-init-local on; /sbin/chkconfig cloud-init on; /sbin/chkconfig cloud-config on; /sbin/chkconfig cloud-final on"
exit

sudo umount $TEMP
sudo rm -r $TEMP

sudo vgchange -an vgroot
sudo qemu-nbd -d /dev/nbd0
sudo pvscan --cache

glance --os-username --os-password image-create $2

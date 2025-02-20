#!/bin/bash

# Default values
IMAGE_FILE="tema2.img"
KERNEL_FILE="vmlinuz-tema2"  # vmlinuz-test / vmlinuz-tema2
DTB_FILE="bcm2837-rpi-3-b.dtb"

# if not using a partitioned image, simply use 'mmcblk0' instead
ROOTDEV="mmcblk0"  # mmcblk0p2
QEMU_MACHINE=raspi3b
SERIAL_FIFO=/tmp/si-tema2-serial0
SERIAL1=
QEMU_NET_FWD="hostfwd=tcp::5555-:22,hostfwd=tcp::8888-:80"
NO_NET=

# parse arguments
while [[ "$#" -gt 0 ]]; do
    case "$1" in
	--image) IMAGE_FILE="$2"; shift ;;
	--kernel) KERNEL_FILE="$2"; shift ;;
	--dtb) DTB_FILE="$2"; shift ;;
	--root) ROOTDEV="$2"; shift ;;
	--serial1) SERIAL1=1 ;;
	--no-net) NO_NET=1 ;;
	--no-fifo) SERIAL_FIFO= ;;
    esac; shift
done

_SERIAL_ARGS=(-serial null -serial mon:stdio)
# note: these are the addresses for rapsi3b!
_KERNEL_EARLYCON="earlycon=uart8250,mmio32,0x3f215040 earlycon=pl011,mmio32,0x3f201000"
_KERNEL_CONSOLE="console=ttyAMA0 console=ttyS1"  # console=ttyAMA0 console=ttyS1 / console=ttyS0 console=ttyS1
if [[ -n "$SERIAL1" ]]; then
    _SERIAL_ARGS=(-serial mon:stdio)
fi

_KERNEL_CMDLINE="$_KERNEL_EARLYCON $_KERNEL_CONSOLE loglevel=8"
_KERNEL_CMDLINE+=" root=/dev/$ROOTDEV rw rootwait rootfstype=ext4 ip=dhcp"
#_KERNEL_CMDLINE+=" dwc_otg.lpm_enable=0 dwc_otg.fiq_fsm_enable=0 "
QEMU_ARGS=( # yep, this is a bash array
	-machine "$QEMU_MACHINE" -m 1024 -smp 4
	-kernel "$KERNEL_FILE" -dtb "$DTB_FILE" -sd "$IMAGE_FILE"
	-append "$_KERNEL_CMDLINE"
 	-nographic -monitor none "${_SERIAL_ARGS[@]}"
	-monitor telnet::45454,server,nowait
	-no-reboot
)
if [[ -n "$SERIAL_FIFO" ]]; then
    rm -f "$SERIAL_FIFO"
    mkfifo "$SERIAL_FIFO"
    QEMU_ARGS+=(
	    -chardev "pipe,path=$SERIAL_FIFO,id=acm"
	    -usb -device "usb-serial,chardev=acm"
    )
fi

# append networking configuration (forward ssh && http)
if [[ -z "$NO_NET" ]]; then
    QEMU_ARGS+=(
	    -device "usb-net,netdev=net0,mac=02:ca:fe:f0:0d:01"
	    -netdev "user,id=net0,$QEMU_NET_FWD"
    )
fi

# disable audio (for qemu 2.x)
export QEMU_AUDIO_DRV=none

echo qemu-system-aarch64 "${QEMU_ARGS[@]}"
exec qemu-system-aarch64 "${QEMU_ARGS[@]}"


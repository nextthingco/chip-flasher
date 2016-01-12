#!/bin/bash

SIZE=$(ls -l /home/ntc/Desktop/CHIP-flasher/flasher/tools/.firmware/tmp/padded-uboot | cut -d\  -f 5)

echo "Padded U-boot size is: ${SIZE}"

echo -e "\n Adding current user to dialout group"
sudo usermod -a -G dialout $(logname)

echo -e "\n Adding current user to plugdev group"
sudo usermod -a -G plugdev $(logname)

newgroup
groups

echo -e "\n Adding udev rule for Allwinner device"
echo -e 'SUBSYSTEM=="usb", ATTRS{idVendor}=="1f3a", ATTRS{idProduct}=="efe8", GROUP="plugdev", MODE="0660" SYMLINK+="usb-chip"
SUBSYSTEM=="usb", ATTRS{idVendor}=="18d1", ATTRS{idProduct}=="1010", GROUP="plugdev", MODE="0660" SYMLINK+="usb-chip-fastboot"
' | sudo tee /etc/udev/rules.d/99-allwinner.rules
sudo udevadm control --reload-rules

echo -e "\n Setting ownership"
sudo chown -R ntc:ntc /home/ntc/flasher 


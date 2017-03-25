# CHIP-Flasher
Flashing and Testing tools for CHIP Production. If you are looking to just flash a single CHIP, please just use the CHIP-tools repository. This CHIP-flasher
repository is used for flashing/testing many CHIPs in parallel, but requires additional configuration to make it work.

## Installation
Remember `sudo apt-get update` before you do anything.

You must
*   Run the install script which will install debian and python packages
*   Create desktop entry (TODO verify it works)
*   run 'python udevmaker.py', copy the file to /etc/udev/rules.d (remove any old ones), and reload the rules

## Application
*   GUI: using the Kivy framework.
`./pro.sh`

## Running
The application can detect when devices are plugged in.
You can modify the variables in config.py to tailor the operator experience

##Logging/Stats
Flashing stats are logged in a sqlite database. Currently a basic UI is in the app

##fonts
If the UI is showing rectangle for characters:
wget http://ftp.us.debian.org/debian/pool/main/f/fonts-android/fonts-droid_4.4.4r2-6_all.deb
dpkg -i fonts*.deb

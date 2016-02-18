#!/bin/bash
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
DISPLAY=:0 sudo kivy ${DIR}/flasher/kivyApp.py ChipHardwareTest

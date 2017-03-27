import os
#specify the .chp file you want to use.
# CHP_FILE_NAME='/home/debian/Desktop/CHIP-flasher/flash_me.chp'
CHP_FILE_NAME=os.environ['HOME'] + '/Downloads/stable-chip-pro-blinkenlights-b1-Toshiba_512M_SLC.chp'

#Note that if you download the file with a browser, it will be ready to use. However, if you want to download from the command line,
#you need to decompress the file explicitly (the browser does this automatically). For example:
# curl -s --compressed https://d2rchup4fs07xx.cloudfront.net/extension/chp-gz/stable-chip-pro-blinkenlights-b1-Toshiba_512M_SLC.chp > flash_me.chp


AUTO_START_ON_DEVICE_DETECTION = False #When this is true, the test suite will be run automatically when polling detects device. Button input to start runs is disabled. In this mode, it is not obvious to spot 201 timeouts
CLICK_TRIGGERS_ALL = True #If any click is equivalent to clicking on all
CLICK_ONLY_APPLIES_TO_SINGLE_201 = True #If true, then operator must explicity click on a 201 row to clear the error. Otherwise, will use value of CLICK_TRIGGERS_ALL above
#also note a fringe case: If device is plugged in but in a non-fel state when the app starts, it will need to be disconnected to clear the 201 failure


DONT_SEND_FASTBOOT_CONTINUE = True #Depending on the .chp file, the device might boot after fastboot. By setting this to TRUE, we prevent that from happening.

VERBOSE = False #whether more details/errors appear in console

#in fel.c, there is a usleep command which pauses the flashing for .25sec. I believe this may be inadequate and causes usb pipe errors
#because the device isn't ready yet. The multiplier below can be used to multiply that time to increase the delay
FEL_SLEEP_MULTIPLIER = 2.0

#This is the file you produced by running udevmaker.py and copying and reloading rules
UDEV_RULES_FILE = '/etc/udev/rules.d/flasher.rules'

#Database
RUN_NAME="ChipPro 1" #An id that is written to the database tables to identify the batch. See Flash Stats/Browse Stats button in right pane
LOG_DB = 'log.db' # SQLite database of logs. It will be prefixed by the hostname_

#Constants to change appearance.
SKIP_IDLE_STATE = True #Not sure if still hooked in If true, then there won't be an idle state between done and testing
SORT_DEVICES = True # Whether the device id from the UDEV file (chip_id_hub_xxx) should be sorted on screen. Sort is numeric
SORT_HUBS = True # Whether the hub name from the UDEV file (chip_id_hub_xxx) should be sorted on screen. Sort is alphabetic

#Constants to change appearance
HUBS_IN_COLUMNS = True # if True, there will be one visual column per hub as defined by the UDEV entry: chip-id-hub-mode
SHOW_STATE = True # if True, shows an Idle.., Testing,  Pass/Fail column. With a 49 port hub, you probably want this to be false

SUCCESS_COLOR = [ 0, 1, 0, 1] # GREEN
FAIL_COLOR = [ 1, 0, 0, 1] # RED
ACTIVE_COLOR = [ 1, 1, 1, 1] # we will use WHITE for active
PASSIVE_COLOR = [ 1, 1, 0, 1] # we will use YELLOW for passive
PROMPT_COLOR = [ 1, .4, .3, 1] # we will use ORANGE for prompts
DISCONNECTED_COLOR = [.3, .3, .3, 1] #when device is disconnected
WHITE_COLOR = [ 1, 1, 1, 1]
YELLOW_COLOR = [ 1, 1, 0, 1]
PAUSED_COLOR = [ 1, .5, 0, 1]

OSX_FONT = "/Library/Fonts/Arial Unicode.ttf"
UBUNTU_FONT = "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf"

RUN_NAME="batch1" #An id that is written to the database tables to identify the batch

#Constants to change behavior. Also see constants in KivyView
SKIP_IDLE_STATE = True # If true, then there won't be an idle state between done and testing
UDEV_RULES_FILE = '/etc/udev/rules.d/flasher.rules'
SORT_DEVICES = True # Whether the device id from the UDEV file (chip_id_hub_xxx) should be sorted on screen. Sort is numeric
SORT_HUBS = True # Whether the hub name from the UDEV file (chip_id_hub_xxx) should be sorted on screen. Sort is alphabetic

AUTO_START_ON_DEVICE_DETECTION = False #When this is true, the test suite will be run automatically when polling detects device. Button input to start runs is disabled
AUTO_START_WAIT_BEFORE_DISCONNECT = 20 #wait n seconds before considering a disconnect to handle switch to FASTBOOT
DONE_WAIT_BEFORE_DISCONNECT = 2 #This only works on flashing, not hw test. Also, requires chip to go back into fastboot after flashing

ALLOW_INDIVIDUAL_BUTTONS = True #True to allow CHIPS to be started individually, False for Flash All
SHOW_ALL_BUTTON = True #True to have an all button on top, False otherwise.
GRAY_OUT_ON_DISCONNECT = False
SHOW_DEVICE_ID_COLUMN=True # True if a column with hostname  is displayed
SHOW_SERIAL_NUMBER_COLUMN=False # True if a serial number column should show
#database of logs. It will be prefixed by the hostname_
LOG_DB = 'log.db'

#number of seconds to wait for a serial connection in hwtest
FIND_SERIAL_TIME = 45

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
RED_COLOR = [1, 0, 0, 1]
GREEN_COLOR = [0, 1, 0, 1]
YELLOW_COLOR = [ 1, 1, 0, 1]
PAUSED_COLOR = [ 1, .5, 0, 1]
BLACK_COLOR = [0, 0, 0, 1]

# The threshhold limits for the NAND test for the hwtest that's run on CHIP
# The output of the NAND test has the form:
# Checking bitflips on NAND... [uncorrectable-bit-flips] [max-correctable-bitflips] [std-dev-of-max-correctable-bitflips]
# for example:
# Checking bitflips on NAND... 0 49.9 1.64012

MAX_UNCORRECTABLE_BITFLIPS = 0
MAX_CORRECTABLE_BITFLIPS = 99
MAX_STD_DEV_CORRECTABLE_BITFLIPS = 10

MAX_BAD_BLOCKS = 100 #max allowed bad blocks in chip hardware test
#MIN_BBT_BLOCKS = 3 # the minimum number of blocks needed for the bad block tables (bbt)
MIN_BBT_BLOCKS = 0 #Temporarily setting to 0 because something seems wrong with the test

EXCLUDE_HW_TESTS = [312,313] #do not try to run these tests


#####################################################################################
SERIAL_NUMBER_COMMAND = "cat /proc/cpuinfo | grep Serial | awk '{print $3}'"
HOSTNAME_SERIAL_FILE="hostnameSerial.log"
HOSTNAME_FORMAT='TN_{:03d}'

HOSTNAME_COUNTER = 0 #this is used as the base number. If HOSTNAME_ADD_PORT is set below, then the port number will be added to this.
HOSTNAME_ADD_PORT = True #This is used for keeping a specific id for each CHIP if they are already physically labeled. The port # (starting at 1) is added to hostname_counter
NAND_TEST_PROJECT="CHIP-nandTests"
NAND_TEST_REPO = "git clone https://{0}:{1}@github.com/NextThingCo/" + NAND_TEST_PROJECT + ".git"
NAND_TEST_FORMAT = "bash startTest.sh {0}"
NAND_TESTS=["dd.sh","nandBonnie.sh","nandStress.sh"]
NAND_TEST_FORCE=None

BOOTSTRAP_SCRIPT="../CHIP-nandTests/bootstrap.sh"
BOOTSTRAP_SERVICE="../CHIP-nandTests/bootstrap.service"
TEST_STRESS_SERVICE="../CHIP-nandTests/testStress.service"


FIXTURE_HOSTNAME_FORMAT='FIX_{:03d}'

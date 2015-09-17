import time
from flasher.utils import call_and_return
from flasher.usb import USB,wait_for_usb
import logging
log = logging.getLogger('flasher')

# FSM callbacks
def on_idle( instance ):
	return "wait-for-fel"

def on_wait_for_fel( instance ):
	log.info( "Waiting for FEL device to be found..." )
	if wait_for_usb("fel"):
		return "upload"
	else:
		return "failure"

def on_upload( instance ):
	log.info( "Updating CHIP firmware and pushing to CHIP" )
	if call_and_return("./chip-update-firmware.sh", "-f") != 0:
		log.info( "Found" )
		return "wait-for-serial"
	else:
		return "failure"

####
def on_wait_for_serial( instance ):
	log.info( "Updating CHIP firmware and pushing to CHIP" )
	if wait_for_usb("serial-gadget"):
		log.info( "Found" )
		return "verify"
	else:
		return "failure"
def on_verify( instance ):
	log.info( "Updating CHIP firmware and pushing to CHIP" )
	if call_and_return("./verify.sh") == 0:
		return "success"
	else:
		return "failure"

def on_success( instance ):
	log.info( "Successfully updated CHIP firmware" )
	time.sleep(5)
	return "idle"

def on_failure( instance ):
	log.error( "Failed to push firmware to CHIP" )
	time.sleep(5)
	return "idle"


fsm = {
	"idle": {
		"name": "Idle",
		"color": [	0,		0,	0,	1],
		"callback": on_idle,
		"trigger-automatically": False
	},
	"wait-for-fel": {
		"name": "Waiting for FEL device",
		"color": [	1,		0,	1,	1],
		"callback": on_wait_for_fel,
		"trigger-automatically": True
	},
	"upload": {
		"name": "Uploading",
		"color": [0.75,	 0.25,	0,	1],
		"callback": on_upload,
		"trigger-automatically": True
	},
	"wait-for-serial": {
		"name": "Waiting for USB Serial Gadget",
		"color": [	1,		1,	1,	1],
		"callback": on_wait_for_serial,
		"trigger-automatically": True
	},
	"verify": {
		"name": "Verifying",
		"color": [	0,		1,	1,	1],
		"callback": on_verify,
		"trigger-automatically": True
	},
	"success": {
		"name": "Success",
		"color": [	0,		1,	0,	1],
		"callback": on_success,
		"trigger-automatically": True
	},
	"failure": {
		"name": "Failure",
		"color": [	1,		0,	0,	1],
		"callback": on_failure,
		"trigger-automatically": True
	},
}

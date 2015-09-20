# -*- coding: utf-8 -*-
import time
from flasher.utils import call_and_return
from flasher.usb import USB,wait_for_usb
import logging
log = logging.getLogger('flasher')

# FSM callbacks
def on_idle( instance ):
	instance.reset_labels()
	return "wait-for-fel"

def on_wait_for_fel( instance ):
	log.info( "Waiting for FEL device to be found..." )
	if wait_for_usb( instance=instance, type="fel", timeout=5 ):
		return "upload"
	else:
		return "failure"

def on_upload( instance ):
	log.info( "Updating CHIP firmware and pushing to CHIP" )
	if call_and_return( instance=instance, cmd=["./chip-update-firmware.sh", "-f"], timeout=60 ) == 0:
		log.info( "Found" )
		return "wait-for-serial"
	else:
		return "failure"

####
def on_wait_for_serial( instance ):
	log.info( "Updating CHIP firmware and pushing to CHIP" )
	if wait_for_usb( instance=instance, type="serial-gadget", timeout=60 ):
		log.info( "Found" )
		return "verify"
	else:
		return "failure"
def on_verify( instance ):
	log.info( "Updating CHIP firmware and pushing to CHIP" )
	if call_and_return( instance=instance, cmd="./verify.sh", timeout=120 ) == 0:
		return "success"
	else:
		return "failure"

def on_success( instance ):
	log.info( "Successfully updated CHIP firmware" )
	return "idle"

def on_failure( instance ):
	log.error( "Failed to push firmware to CHIP" )
	return "idle"

fsm_order = ['idle', 'wait-for-fel', 'upload', 'wait-for-serial', 'verify', 'success', 'failure']
fsm = {
	"idle": {
		"name": "Ready\n已准备，待连接",
		"color": [	0,		0,	0,	1],
		"callback": on_idle,
		"trigger-automatically": False
	},
	"wait-for-fel": {
		"name": "Searching for FEL...\n连接中",
		"color": [	1,		0,	1,	1],
		"callback": on_wait_for_fel,
		"trigger-automatically": True
	},
	"upload": {
		"name": "Uploading...\n正在加载固件",
		"color": [0.75,	 0.25,	0,	1],
		"callback": on_upload,
		"trigger-automatically": True
	},
	"wait-for-serial": {
		"name": "Booting...\n启动中",
		"color": [	1,		1,	1,	1],
		"callback": on_wait_for_serial,
		"trigger-automatically": True
	},
	"verify": {
		"name": "Verifying...\n验证中",
		"color": [	0,		1,	1,	1],
		"callback": on_verify,
		"trigger-automatically": True
	},
	"success": {
		"name": "PASS\n通过",
		"color": [	0,		1,	0,	1],
		"callback": on_success,
		"trigger-automatically": False
	},
	"failure": {
		"name": "FAIL\n失败",
		"color": [	1,		0,	0,	1],
		"callback": on_failure,
		"trigger-automatically": False
	},
}

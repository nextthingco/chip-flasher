# -*- coding: utf-8 -*-
from flasher import fsm
from flasher.utils import call_and_return
from flasher.usb import USB,wait_for_usb
from flasher.persistentdata import PersistentData
from flasher.logmanager import LogManager

# FSM callbacks
@fsm.station( "station-c" )
class StationC( fsm.FSM ):
	@fsm.list_index( 10 )
	@fsm.name( "Ready\n已准备，待连接" )
	@fsm.color( [	0,		0,	0,	1] )
	@fsm.trigger_automatically( False )
	def on_idle( instance ):
		instance.reset_labels()

		chip_id = PersistentData.get( "flash-count" )
		chip_id = chip_id + 1
		PersistentData.set( "flash-count", chip_id )
		PersistentData.write()
		return "on_wait_for_serial"

	@fsm.list_index( 30 )
	@fsm.name( "Searching for Login.\n启动中" )
	@fsm.color( [	1,		1,	1,	1] )
	@fsm.trigger_automatically( True )
	def on_wait_for_serial( instance ):
		chip_id = PersistentData.get( "flash-count" )
		log = LogManager.get_instanced_log( chip_id )
		log.info( "Updating CHIP firmware and pushing to CHIP" )
		if wait_for_usb( instance=instance, type="serial-gadget", log=log, timeout=60 ):
			log.info( "Found" )
			return "on_verify"
		else:
			return "on_failure"

	@fsm.list_index( 40 )
	@fsm.name( "Verifying...\n验证中" )
	@fsm.color( [	0,		1,	1,	1] )
	@fsm.trigger_automatically( True )
	def on_verify( instance ):
		chip_id = PersistentData.get( "flash-count" )
		log = LogManager.get_instanced_log( chip_id )
		log.info( "Updating CHIP firmware and pushing to CHIP" )
		if call_and_return( instance=instance, cmd="./verify.sh", log=log, timeout=120 ) == 0:
			return "on_success"
		else:
			return "on_failure"

	@fsm.list_index( 50 )
	@fsm.name( "Verifying...\n验证中" )
	@fsm.color( [	0,		1,	1,	1] )
	@fsm.trigger_automatically( True )
	def on_verify( instance ):
		chip_id = PersistentData.get( "flash-count" )
		log = LogManager.get_instanced_log( chip_id )
		log.info( "Updating CHIP firmware and pushing to CHIP" )
		if call_and_return( instance=instance, cmd="./verify.sh", log=log, timeout=120 ) == 0:
			return "on_success"
		else:
			return "on_failure"

	@fsm.list_index( 60 )
	@fsm.name( "PASS\n通过" )
	@fsm.color( [	0,		1,	0,	1] )
	@fsm.trigger_automatically( False )
	def on_success( instance ):
		chip_id = PersistentData.get( "flash-count" )
		log = LogManager.get_instanced_log( chip_id )
		log.info( "Successfully updated CHIP firmware" )
		return "on_idle"

	@fsm.list_index( 70 )
	@fsm.name( "FAIL\n失败" )
	@fsm.color( [	1,		0,	0,	1] )
	@fsm.trigger_automatically( False )
	def on_failure( instance ):
		chip_id = PersistentData.get( "flash-count" )
		log = LogManager.get_instanced_log( chip_id )
		log.error( "Failed to push firmware to CHIP" )
		return "on_idle"
# -*- coding: utf-8 -*-
from flasher import fsm
from flasher.utils import call_and_return
from flasher.usb import USB,wait_for_usb
from flasher.persistentdata import PersistentData
from flasher.logmanager import LogManager
		
# FSM callbacks
@fsm.station( "station-b" )
class StationB( fsm.FSM ):
	@fsm.list_index(1)
	@fsm.name( "Ready\n已准备，待连接" )
	@fsm.color( [	0,		0,	0,	1] )
	@fsm.trigger_automatically( False )
	def on_idle( instance ):
		instance.reset_labels()

		chip_id = PersistentData.get( "flash-count" )
		chip_id = chip_id + 1
		PersistentData.set( "flash-count", chip_id )
		PersistentData.write()
		return "on_wait_for_fel"

	@fsm.list_index( 1 )
	@fsm.name( "Searching for FEL...\n连接中" )
	@fsm.color( [	1,		0,	1,	1] )
	@fsm.trigger_automatically( True )
	def on_wait_for_fel( instance ):
		chip_id = PersistentData.get( "flash-count" )
		log = LogManager.get_instanced_log( chip_id )
		log.info( "Waiting for FEL device to be found..." )
		if wait_for_usb( instance=instance, type="fel", log=log, timeout=5 ):
			return "on_upload"
		else:
			return ( "on_failure", "FEL Not Found!" )

	@fsm.list_index( 2 )
	@fsm.name( "Uploading...\n正在加载固件" )
	@fsm.color( [0.75,	 0.25,	0,	1] )
	@fsm.trigger_automatically( True )
	def on_upload( instance ):
		err_codes = {
			-1: "Unknown Failure",
			128: "FEL Error.",
			129: "DRAM Error?",
			130: "Upload Error.",
			131: "Upload Error.",
			132: "Bad Cable?",
			133: "Fastboot fail.",
			134: "Fastboot fail.",
			135: "Bad U-boot."
		}
		chip_id = PersistentData.get( "flash-count" )
		log = LogManager.get_instanced_log( chip_id )
		log.info( "Updating CHIP firmware and pushing to CHIP" )
		errcode = call_and_return( instance=instance, cmd=["./chip-fel-flash.sh", "-f"], log=log, timeout=400 )
		if errcode == 0:
			log.info( "Found" )
			return "on_success"
		else:
			if not errcode in err_codes:
				errcode = -1
			return ( "on_failure", err_codes[ errcode ] )

	@fsm.list_index( 3 )
	@fsm.name( "PASS\n通过" )
	@fsm.color( [	0,		1,	0,	1] )
	@fsm.trigger_automatically( False )
	def on_success( instance ):
		chip_id = PersistentData.get( "flash-count" )
		log = LogManager.get_instanced_log( chip_id )
		log.info( "Successfully updated CHIP firmware" )
		return "on_idle"

	@fsm.list_index( 4 )
	@fsm.name( "FAIL\n失败" )
	@fsm.color( [	1,		0,	0,	1] )
	@fsm.trigger_automatically( False )
	def on_failure( instance ):
		chip_id = PersistentData.get( "flash-count" )
		log = LogManager.get_instanced_log( chip_id )
		log.error( "Failed to push firmware to CHIP" )
		return "on_idle"

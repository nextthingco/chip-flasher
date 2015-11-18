# -*- coding: utf-8 -*-
from flasher import fsm
from flasher.utils import call_and_return
from flasher.usb import USB,wait_for_usb
from flasher.persistentdata import PersistentData
from flasher.logmanager import LogManager
from testjig.ChipTest import TestSuite as ChipTester

test = ChipTester("/dev/ttyACM2")
# FSM callbacks
@fsm.station( "station-b" )
class StationB( fsm.FSM ):
	@fsm.list_index( 1 )
	@fsm.name( "Ready\n已准备，待连接" )
	@fsm.color( [	0,		0,	0,	1] )
	@fsm.trigger_automatically( False )
	def on_idle( instance ):
		instance.reset_labels()

		chip_id = PersistentData.get( "flash-count" )
		chip_id = chip_id + 1
		PersistentData.set( "flash-count", chip_id )
		PersistentData.write()
		return "on_power_test"

	@fsm.list_index( 5 )
	@fsm.name( "Power Test" )
	@fsm.color( [	0,		0,	0,	1] )
	@fsm.trigger_automatically( True )
	def on_power_test( instance ):
		try:
			test.testA()
			return "on_upload"
		except Exception as e:
			print( "Failed Test Suite: \n" + str( e.args ) )
			return ( "on_failure", e.args[0] )

	@fsm.list_index( 30 )
	@fsm.name( "Uploading...\n正在加载固件" )
	@fsm.color( [0.75,	 0.25,	0,	1] )
	@fsm.trigger_automatically( True )
	def on_upload( instance ):
		def flasher_function():
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
			print("Waiting for USB")
			if wait_for_usb( instance=instance, type="fel", log=log, timeout=30 ):
				print("Running chip-fel-flash")
				errcode = call_and_return( instance=instance, cmd=["./chip-fel-flash.sh", "-f"], log=log, timeout=400 )
				errcode = 0
				print("Error code: " + str(errcode) )
				if errcode != 0:
					if not errcode in err_codes:
						errcode = -1
					raise Exception( "Flashing failed: ", err_codes[ errcode ] )
			else:
				raise Exception( "Flashing failed: ", "Could not find FEL device" )
		try:
			chip_id = PersistentData.get( "flash-count" )
			log = LogManager.get_instanced_log( chip_id )
			log.info( "Updating CHIP firmware and pushing to CHIP" )
			test.testB( flasher_function )
			return "on_verify"
		except Exception as e:
			print( "Failed Test Suite: \n" + str( e.args ) )
			return ( "on_failure", e.args[0] )

	@fsm.list_index( 60 )
	@fsm.name( "Verifying...\n验证中" )
	@fsm.color( [   0,              1,      1,      1] )
	@fsm.trigger_automatically( True )
	def on_verify( instance ):
		def tester_function():
			chip_id = PersistentData.get( "flash-count" )
			log = LogManager.get_instanced_log( chip_id )
			log.info( "Updating CHIP firmware and pushing to CHIP" )
			if not wait_for_usb( instance=instance, type="serial-gadget", log=log, timeout=120 ):
				raise Exception( "Flashing failed: ", "Vould not find serial gadget!" )
			if call_and_return( instance=instance, cmd="./verify.sh", log=log, timeout=120 ) != 0:
				raise Exception( "Flashing failed: ", "Verify script failed!" )
		try:
			test.testC( tester_function )
			return "on_success"
		except Exception as e:
			print( "Failed Test Suite: \n" + str( e.args ) )
			return ( "on_failure", e.args[0] )


	@fsm.list_index( 100 )
	@fsm.name( "PASS\n通过" )
	@fsm.color( [	0,		1,	0,	1] )
	@fsm.trigger_automatically( False )
	def on_success( instance ):
		chip_id = PersistentData.get( "flash-count" )
		log = LogManager.get_instanced_log( chip_id )
		log.info( "Successfully updated CHIP firmware" )
		return "on_idle"

	@fsm.list_index( 101 )
	@fsm.name( "FAIL\n失败" )
	@fsm.color( [	1,		0,	0,	1] )
	@fsm.trigger_automatically( False )
	def on_failure( instance ):
		chip_id = PersistentData.get( "flash-count" )
		log = LogManager.get_instanced_log( chip_id )
		log.error( "Failed to push firmware to CHIP" )
		return "on_idle"

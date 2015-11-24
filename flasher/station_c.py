# -*- coding: utf-8 -*-
from flasher import fsm
from flasher.utils import call_and_return
from flasher.usb import USB,wait_for_usb
from flasher.persistentdata import PersistentData
from flasher.logmanager import LogManager
from flasher.serialconnection import SerialConnection
import re

#from obsub import event
# globalSerialConnection = None

#pip install obsub
# FSM callbacks


@fsm.station( "station-c" )
class StationC( fsm.FSM ):
	
	def __init__(self):
		self.serialConnection = SerialConnection()
		globalSerialConnection = self.serialConnection
	
	@fsm.list_index( 10 )
	@fsm.name( "Ready\n已准备，待连接" )
	@fsm.color( [	0,		0,	0,	1] )
	@fsm.trigger_automatically( False )
	def on_idle(instance ):
		instance.reset_labels()

		chip_id = PersistentData.get( "flash-count" )
		chip_id = chip_id + 1
		PersistentData.set( "flash-count", chip_id )
		PersistentData.write()
		return "on_hwtest"


	@fsm.list_index( 40 )
	@fsm.name( "Verifying...\n验证中" )
	@fsm.color( [	0,		1,	1,	1] )
	@fsm.trigger_automatically( True )
	def on_hwtest(instance ):
		chip_id = PersistentData.get( "hwtest" )
		log = LogManager.get_instanced_log( chip_id )
		log.info( "Running hwtest on CHIP" )
		result = 0
		try:
			serialConnection = SerialConnection()
			serialConnection.doLogin()
# 			hwTestResult = self.serialConnection.send("hwtest",timeout=60)
			hwTestResult = serialConnection.send("hwtest",timeout=60)
			if re.search(r'.*### ALL TESTS PASSED ###.*',hwTestResult):
				result = 0
				print "---> TESTS PASSED"
			else:
				result = 1
				print "---> TESTS FAILED"
		except Exception, e:
			print e
			print "---> TESTS FAILED - EXCEPTION"
			result =  2
		finally:
			serialConnection.close()
			
		if result == 0:
			return "on_success"
		else:
			return "on_failure"


	@fsm.list_index( 60 )
	@fsm.name( "PASS\n通过" )
	@fsm.color( [	0,		1,	0,	1] )
	@fsm.trigger_automatically( False )
	def on_success(instance ):
		chip_id = PersistentData.get( "hwtest" )
		log = LogManager.get_instanced_log( chip_id )
		log.info( "Successfully tested hwardwareware" )
		return "on_idle"

	@fsm.list_index( 70 )
	@fsm.name( "FAIL\n失败" )
	@fsm.color( [	1,		0,	0,	1] )
	@fsm.trigger_automatically( False )
	def on_failure(instance ):
		chip_id = PersistentData.get( "hwtest" )
		log = LogManager.get_instanced_log( chip_id )
		log.error( "Failed testing CHIP hardware" )
		return "on_idle"
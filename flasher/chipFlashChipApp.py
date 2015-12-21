# -*- coding: utf-8 -*-

from deviceDescriptor import DeviceDescriptor
from ui_strings import *
from controller import Controller
from scheduler import call_repeatedly
from logging import log
import logging
import sys

class ChipFlashChipApp():
	def __init__( self, testSuiteName ):
		logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
		self.log = logging.getLogger("flash")

		self.controller = Controller(log, testSuiteName)
		self.controller.setTimeoutMultiplier(2.3)
							
	def run( self ):
		self.controller.configure()
		self.view = ChipFlashChipView(deviceDescriptors=self.controller.deviceDescriptors, hubs = self.controller.hubs)
		self.controller.addStateListener(self.view.onUpdateStateInfo.__get__(self.view,ChipFlashChipView))
		
		call_repeatedly(1, lambda: self.controller.onPollingTick(0))
		call_repeatedly(.1,lambda: self.controller.onUpdateTrigger(0))
# 		call_repeatedly(1, self._onPollingTick.__get__(self,ChipFlashChipApp))
# 		call_repeatedly(.1, self._onUpdateTrigger.__get__(self,ChipFlashChipApp))

		return self.view
	
# 	def _onUpdateTrigger(self):
# 		self.controller.onUpdateTrigger(0)
# 
# 	def _onPollingTick(self):
# 		self.controller.onPollingTick(0)

		
class ChipFlashChipView():

	def __init__( self, **kwargs ):
		'''
		The view part of the MVC. note that some values are passed in the kwargs dict. See below
		Basically, this method will create and layout the gui's widgets
		'''
		self.deviceDescriptors = kwargs['deviceDescriptors']
		self.hubs = kwargs['hubs']
		for i,hub in enumerate(self.hubs): #go through the hubs
			for key, deviceDescriptor in self.deviceDescriptors.iteritems(): #now go through devices
				if deviceDescriptor.hub != hub:
					continue #not on this hub, ignore
				
		
	
	def onUpdateStateInfo(self, info):
		'''
		Observer callback from main thread
		:param info:
		'''
		'''
		Kivy has threading issues if you try to update GUI components from a child thread.
		The solution is to add a @mainthread attribute to a function in the chlid class.
		This function will then run in the main thread. It, in turn, calls this method
		info.uid: The port
		info.state: corresponds to the states. e.g. PASSIVE_STATE
		info.stateLabel: Text label for the state, such as RUNNING_TEXT
		info.label: The label for the test case that is being run
		info.progress: number value for progress bar
		info.output: The output for the test case
		info.prompt: Any prompt to show
		'''
		uid = info['uid']
		state = info.get('state')
		stateLabel = info.get('stateLabel')
		label = info.get('label')
		progress = info.get('progress')
		output = info.get('output')
		prompt = info.get('prompt')
		print info
			
######################################################################################################################################
# Privates
######################################################################################################################################

########################################################################################
if __name__ == '__main__':
	app = ChipFlashChipApp("Flasher")
	try:
		app.run()
	except (KeyboardInterrupt, SystemExit):
		app.stop()
    
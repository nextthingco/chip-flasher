# -*- coding: utf-8 -*-
	
from os import path
from deviceDescriptor import DeviceDescriptor
from runState import RunState

import subprocess
import unittest
from collections import OrderedDict
from flasher import Flasher
from chipHardwareTest import ChipHardwareTest
from ui_strings import *
from testingThread import TestingThread,TestResult
from Queue import Queue
import time
# 
# try:
# 	LogManager #see if it exists
# 	log = LogManager.get_global_log()
# except:
# 	import logging
# 	logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
# 	log = logging.getLogger("flasher")
	
get_class = lambda x: globals()[x]

#Constants to change behavior. Also see constants in KivyView
SKIP_IDLE_STATE = True # If true, then there won't be an idle state between done and testing
UDEV_RULES_FILE = '/etc/udev/rules.d/flasher.rules'
#UDEV_RULES_FILE = 'flasher.rules'
SORT_DEVICES = True # Whether the device id from the UDEV file (chip_id_hub_xxx) should be sorted on screen. Sort is numeric
SORT_HUBS = True # Whether the hub name from the UDEV file (chip_id_hub_xxx) should be sorted on screen. Sort is alphabetic

AUTO_START_ON_DEVICE_DETECTION = True #When this is true, the test suite will be run automatically when polling detects device. Button input to start runs is disabled
AUTO_START_WAIT_BEFORE_DISCONNECT = 20 #wait n seconds before considering a disconnect to handle switch to FASTBOOT



class Controller():
	'''
	The main application for a GUI-based, parallel test suite runner
	'''
	def __init__( self, log = None, testSuiteName=None ):
		cwd = path.dirname( path.dirname( path.realpath( __file__ ) ) )
		self.log = log
		self.testSuiteName = testSuiteName
		self.testThreads = {}
		self.runStates = {}
		self.stateInfo = OrderedDict() # keep track of last known state info
		self.deviceDescriptors, self.hubs = DeviceDescriptor.readRules(UDEV_RULES_FILE, SORT_DEVICES, SORT_HUBS)
		self.deviceStates = {} # keep track of the last know state of each device. Used when polling for unplug/replugs
		self.mutexes = {}
		self.count = 0 #number of CHIPS passed thorugh
		self.autoStartOnDeviceDetection = AUTO_START_ON_DEVICE_DETECTION #This should be command line argument
		# Below is for managing the GUI via an update queue. Kivy requires thread sync on GUI updates
		# Note that I tried using a @mainthread decorator to make things thread safe, but the problem with that is the order of events isn't preserved
		self.updateQueue = UpdateQueue(self._triggerUpdate.__get__(self,Controller)) # A thread-safe queue for managing GUI updates in order
		self.updateQueueListeners = [] #listeners get called when something is added to queue
		self.stateListeners = []
		self.timeoutMultiplier = 1.0 #increase on slow flashing machines
		self.onlyBroadcastLastChange = True #whether to batch updates
	def configure( self ):
		'''
		Kivy will call this method to start the app
		'''
		
		self.rev = 0
		self.hostname = ""
		self.build_string = ""
		currentTime = time.time() 

		for key, deviceDescriptor in self.deviceDescriptors.iteritems():
			self.runStates[key] = RunState(key) #make a new object to store the state info
			self.stateInfo[key] = {'uid':key} #each one is a dictionary
			self.deviceStates[key] = (DeviceDescriptor.DEVICE_NULL, currentTime)
		


	def addStateListener(self,listener):
		self.stateListeners.append(listener)
	
	def onPollingTick(self,dt):
		self._checkAndTriggerDeviceChanges(dt)

	def onMainButton(self, button):
		'''
		Handle button clicks on id column as triggers to do something
		:param button:
		'''
		self._onTriggerDevice(button.id)

	def getTitle( self ):
		'''
		Display the app title
		'''
		cwd = path.dirname( path.dirname( path.realpath( __file__ ) ) )
		hostname = subprocess.Popen( ["hostname"],cwd=cwd, stdout=subprocess.PIPE ).communicate()[0].strip("\n")
		
		rev = subprocess.Popen( ["git", "rev-parse","HEAD"],cwd=cwd, stdout=subprocess.PIPE ).communicate()[0].strip("\n")
		try:
			with open(cwd+"/tools/.firmware/images/build") as myfile:
				build_string = myfile.read().strip("\n")
		except:
			build_string = ""

		self.build_string = build_string
		self.rev = rev
		self.hostname = hostname
		return self.testSuiteName + ": Host: " + self.hostname + " | Revision: " + self.rev[0:10] + " | Firmware Build: " + self.build_string


	def addUpdateQueueListener(self,listener):
		'''
		Add a listener taht will be called when something is added to the queue
		:param listener:
		'''
		self.updateQueueListeners.append(listener)

	def onUpdateTrigger(self,x):
		'''
		This method is called by Kivy's Clock object before the next frame when self.kivyUpdateTrigger() has been called
		'''
		while not self.updateQueue.empty(): #process everything in the queue
			info = self.updateQueue.get()
			last = self.updateQueue.empty()
			self._updateStateInfo(info,last)
				
	def setTimeoutMultiplier(self, timeoutMultiplier):
		self.timeoutMultiplier = timeoutMultiplier
######################################################################################################################################
# Privates
######################################################################################################################################
	def _checkAndTriggerDeviceChanges(self, dt):
		'''
		This is a Kivy.Clock callback that will see if any devices have been plugged or unplugged.
		If so, it will start or stop their runs by triggering an event on them
		:param dt:
		'''
		'''
		Go through the device descriptors and see if any state changed
		'''
		currentTime = time.time() 

		for uid, deviceDescriptor in self.deviceDescriptors.iteritems():
			currentState = deviceDescriptor.getDeviceState()
			lastKnownState, when = self.deviceStates[uid]
			elapsedTime = currentTime - when #see how long its been since we
			if lastKnownState != currentState: #if the state is different since last time
# 				print "state : lastKnown: " + str(lastKnownState) + " current " + str(currentState) + " elapsed " + str(elapsedTime)
				if currentState == DeviceDescriptor.DEVICE_FASTBOOT:
					self.deviceStates[uid] = (currentState, currentTime) #just update the time. don't trigger
				elif currentState == DeviceDescriptor.DEVICE_DISCONNECTED:
					if lastKnownState == DeviceDescriptor.DEVICE_WAITING_FOR_FASTBOOT:
						if elapsedTime < AUTO_START_WAIT_BEFORE_DISCONNECT: # wait for possible transition. 
							self.deviceStates[uid] = (DeviceDescriptor.DEVICE_WAITING_FOR_FASTBOOT, currentTime)
							continue
						else: # a disconnect
							self.deviceStates[uid] = (currentState, currentTime)
							self._onTriggerDevice(uid,currentState) #disconnect
							
					elif lastKnownState == DeviceDescriptor.DEVICE_FEL: #if went from fel to nothing, probably transitioning to fastboot
						self.deviceStates[uid] = (DeviceDescriptor.DEVICE_WAITING_FOR_FASTBOOT, currentTime)
						continue # don't update state info
					elif lastKnownState == DeviceDescriptor.DEVICE_FASTBOOT:
						continue #preserve state
					elif lastKnownState == DeviceDescriptor.DEVICE_SERIAL:
						continue #preserve state
					self.deviceStates[uid] = (currentState, currentTime)
					self._onTriggerDevice(uid,currentState) #disconnect
				else: #for FEL and serial gadget
					self.deviceStates[uid] = (currentState, currentTime)
					self._onTriggerDevice(uid,currentState)
			else:
				self.deviceStates[uid] = (currentState, currentTime)
				
					

	deviceStateToTestSuite = {DeviceDescriptor.DEVICE_FEL:'Flasher', DeviceDescriptor.DEVICE_SERIAL: 'ChipHardwareTest'}
	
	def _loadSuite(self, deviceState = None):
		'''
		Loads the test suite to run
		:param deviceState If given, it will determine what suite to run automatically.
		       When runing
		'''
		tl = unittest.TestLoader()
		if deviceState:
			suiteName = self.deviceStateToTestSuite[deviceState]
		else:
			suiteName = self.testSuiteName
		suite = tl.loadTestsFromTestCase(get_class(suiteName))
		return suite
	
	def _getActiveThread(self,uid):
		'''
		Gets the active thread associated with a uid, if any. If the thread is not active, returns None
		:param uid:
		'''
		if uid in self.testThreads:
			testingThread = self.testThreads.get(uid) #get the thread
			if testingThread and not testingThread.isAlive():
				self.testThreads[uid] = None #if the thread is dead, remove it from the dictionary
				testingThread = None
			return testingThread
		
	def _abortThread(self,uid):
		'''
		If the thread should be considered dead - happens when device is removed abruptly
		:param uid:
		'''
		testingThread = self.testThreads.get(uid) #get the thread
		if testingThread:
			testingThread.aborted = True
		self.testThreads[uid] = None
				
	def _onTriggerDevice(self,uid, deviceState = None):
		'''
		Trigger an event for the id. This can either start a test run, clear a prompt, or move from done state to idle state
		:param button: Button that was clicked on
		'''
		if deviceState == DeviceDescriptor.DEVICE_DISCONNECTED: #device was unplugged
			self._abortThread(uid)
			self._updateStateInfo({'uid':uid, 'state': RunState.DISCONNECTED_STATE}) #purposely not showing DISCONNECTED_TEXT because it may be useful to keep info on screen
			return	
				
		testingThread = self._getActiveThread(uid)
		#The button is always bound. How it is treated depends on the meta state and whether the thread (if any) is waiting for a click
		if testingThread:
			testingThread.processButtonClick() #maybe the thread has a prompt and wants to wake up
			return
		
		if self.autoStartOnDeviceDetection and not deviceState: #ignore button clicks if in polling mode
			return
		
		runState = self.runStates[uid]
		deviceDescriptor = self.deviceDescriptors[uid]

		if runState.isDone(): #if currently in a PASS or FAIL state
			self._updateStateInfo({'uid': uid, 'state': RunState.PASSIVE_STATE, 'stateLabel': WAITING_TEXT, 'label': ' '}) #labelcannot be "". It needs to be a space
			self.output = ""
			if not SKIP_IDLE_STATE:
				self._updateStateInfo({'uid': uid, 'state': RunState.IDLE_STATE, 'stateLabel': WAITING_TEXT, 'label': ' ', 'output': ' '}) #label cannot be "". It needs to be a space 
				return


		self._updateStateInfo({'uid':uid, 'state': RunState.ACTIVE_STATE, 'stateLabel': RUNNING_TEXT})
		if deviceState and not self.autoStartOnDeviceDetection: # if we just want graying out behavior
			self._updateStateInfo({'uid': uid, 'state': RunState.IDLE_STATE, 'stateLabel': WAITING_TEXT, 'label': ' ', 'output': ' '}) #label cannot be "". It needs to be a space 
			return

		suite = self._loadSuite(deviceState)
		testResult = TestResult()
		self.count += 1 #processing another one!
		
		testThread = TestingThread(self.log, suite, deviceDescriptor, self.count, self.mutexes, self.updateQueue, testResult, self.timeoutMultiplier) #reesult will get written to testResult
		self.testThreads[uid] = testThread
		testThread.start() #start the thread, which will call runTestSuite

	
	def _updateStateInfo(self, info,last=True):
		'''
		update the run state and notify any listeners
		info.uid: The port
		info.state: corresponds to the states. e.g. PASSIVE_STATE
		info.stateLabel: Text label for the state, such as RUNNING_TEXT
		info.label: The label for the test case that is being run
		info.progress: number value for progress bar
		info.output: The output for the test case
		info.prompt: Any prompt to show
		'''
		uid = info['uid']
 		self.stateInfo[uid].update(info) #merge in latest state info
# 		print self.stateInfo[uid]
		state = info.get('state')
		output = info.get('output')
		
		runState = self.runStates[uid]
		
		if state:
			runState.state = state
			
		if output:
			runState.output = output

		#notify listeners of the change so they can update their UI
		if self.onlyBroadcastLastChange and last:
			for listener in self.stateListeners:
				listener(self.stateInfo[uid])
		else:
			for listener in self.stateListeners:
				listener(info)
		
	
	def _triggerUpdate(self):
		'''
		The UpdateQueue will call these listener method every time something is added to the queue.
		'''
		for listener in self.updateQueueListeners:
			listener()
# 		self.kivyUpdateTrigger() #trigger the main kivy thread to look in the UpdateQueue
		


class UpdateQueue(Queue):
	'''
	Modifed from comment here: http://stackoverflow.com/questions/22031262/altering-a-kivy-property-from-another-thread
    A Multithread safe class that calls a callback whenever an item is added
    to the queue. Instead of having to poll or wait, you could wait to get
    notified of additions.
    '''

	notify_func = None
	parent = None

	def __init__(self, notify_func, **kwargs):
		'''
		:param notify_func:The function to call when adding to the queue
		'''
		Queue.__init__(self, **kwargs)
		self.notify_func = notify_func
	def put(self, info):
		'''
	    Adds a dictionary the queue and calls the callback function.
		'''
		Queue.put(self, info, False)
		self.notify_func()
	
	def get(self):
		'''
	    Returns the next items in the queue, if non-empty, otherwise a
	    :py:attr:`Queue.Empty` exception is raised.
	    '''
		return Queue.get(self, False)

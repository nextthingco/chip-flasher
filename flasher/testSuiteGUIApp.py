# -*- coding: utf-8 -*-
from kivy.config import Config

# Config.set('graphics', 'fullscreen', '1')
Config.set('graphics', 'width', '1024')
Config.set('graphics', 'height', '768')
Config.set('graphics', 'window_state',"maximized")
from kivy.app import App
from kivy.clock import Clock
from persistentdata import PersistentData
from os import path
from deviceDescriptor import DeviceDescriptor
from testSuiteGUIView import *

import subprocess
import unittest
from flasher import Flasher
from chipHardwareTest import ChipHardwareTest
from ui_strings import *
from testingThread import *
from Queue import Queue
from guiContants import *

log = LogManager.get_global_log()
get_class = lambda x: globals()[x]

#Constants to change behavior. Also see constants in TestSuiteGUIView
SKIP_IDLE_STATE = True # If true, then there won't be an idle state between done and testing
UDEV_RULES_FILE = '/etc/udev/rules.d/flasher.rules'
# UDEV_RULES_FILE = 'flasher49.rules'
SORT_DEVICES = True # Whether the device id from the UDEV file (chip_id_hub_xxx) should be sorted on screen. Sort is numeric
SORT_HUBS = True # Whether the hub name from the UDEV file (chip_id_hub_xxx) should be sorted on screen. Sort is alphabetic

	
class TestSuiteGUIApp( App ):
	'''
	The main application for a GUI-based, parallel test suite runner
	'''
	def __init__( self, testSuiteName ):
		super( TestSuiteGUIApp, self ).__init__()
		cwd = path.dirname( path.dirname( path.realpath( __file__ ) ) )
		self.testSuiteName = testSuiteName
		PersistentData.read() #unused for now
		self.testThreads = {}
		self.deviceUIInfo = {}
		self.deviceDescriptors, self.hubs = DeviceDescriptor.readRules(UDEV_RULES_FILE, SORT_DEVICES, SORT_HUBS)
		self.outputDetailUid = None #the uid of of what's being shown in the output (detail) view to the right of the splitter
		self.mutexes = {}
		self.count = 0 #number of CHIPS passed thorugh
		
		# Below is for managing the GUI via an update queue. Kivy requires thread sync on GUI updates
		# Note that I tried using a @mainthread decorator to make things thread safe, but the problem with that is the order of events isn't preserved
		self.updateQueue = KivyQueue(self._triggerUpdate.__get__(self,TestSuiteGUIApp)) # A thread-safe queue for managing GUI updates in order
		self.kivyUpdateTrigger = Clock.create_trigger(self._onUpdateTrigger.__get__(self,TestSuiteGUIApp)) #kivy Trigger that will be set when added to queue

	def build( self ):
		'''
		Kivy will call this method to start the app
		'''
		self.rev = 0
		self.hostname = ""
		self.build_string = ""
		self._displayTitle()
		
		#Process the device descriptors and connect them to GUI's buttons
		self.view = TestSuiteGUIView(deviceDescriptors=self.deviceDescriptors, hubs = self.hubs, deviceUIInfo = self.deviceUIInfo)
		for key in self.deviceUIInfo:
			deviceUIInfo = self.deviceUIInfo[key]
			deviceUIInfo.widgetInfo['button'].bind( on_press=self._onClickedMainButton.__get__(self, TestSuiteGUIApp))
			deviceUIInfo.widgetInfo['label'].bind( on_press=self._onShowOutput.__get__(self, TestSuiteGUIApp))

		return self.view

	def on_stop( self ):
		'''
		Called from Kivy at end of run
		'''
# 		PersistentData.write()
# 		LogManager.close_all_logs()
		pass

######################################################################################################################################
# Privates
######################################################################################################################################
	def _loadSuite(self):
		'''
		Loads the test suite to turn
		'''
		tl = unittest.TestLoader()
		suite = tl.loadTestsFromTestCase(get_class(self.testSuiteName))
		return suite
	
		
	def _displayTitle( self ):
		'''
		Display the app title
		'''
		cwd = path.dirname( path.dirname( path.realpath( __file__ ) ) )
		hostname = subprocess.Popen( ["hostname"],cwd=cwd, stdout=subprocess.PIPE ).communicate()[0].strip("\n")
		if hostname != self.hostname:
			log.info( "Host: " + hostname )
		
		rev = subprocess.Popen( ["git", "rev-parse","HEAD"],cwd=cwd, stdout=subprocess.PIPE ).communicate()[0].strip("\n")
		if rev != self.rev:
			log.info( "Flasher Revision: " + rev[0:10] )
		try:
			with open(cwd+"/tools/.firmware/images/build") as myfile:
				build_string = myfile.read().strip("\n")
		except:
			build_string = ""

		if build_string != self.build_string:
			log.info( "Firmware Build: " + build_string )
		self.build_string = build_string
		self.rev = rev
		self.hostname = hostname
		self.title = self.testSuiteName + ": Host: " + self.hostname + " | Revision: " + self.rev[0:10] + " | Firmware Build: " + self.build_string


	def _onShowOutput(self,button,uid = None):
		'''
		Show the output for the currently selected port (by clicking on its label column, not port column
		:param button: this will be the id of the port if invoked through button. Null if called explicitly
		:param uid: Id of the port to show
		'''
		if uid:
			if self.outputDetailUid != uid: #skip if trying to update output, but parent isnt showing it
				return
		else:
			uid = button.id
		self.outputDetailUid = uid # signify that we want to show this port now
		if uid in self.deviceUIInfo:
			deviceUIInfo = self.deviceUIInfo[uid]
			title = "Port: " + str(uid)
			self.view.setOutputDetailTitle(title)
			self.view.output.text=deviceUIInfo.output

	def _getActiveThread(self,uid):
		'''
		Gets the active thread associated with a uid, if any. If the thread is not active, returns None
		:param uid:
		'''
		if uid in self.testThreads:
			testingThread = self.testThreads[uid] #get the thread
			if testingThread and not testingThread.isAlive():
				self.testThreads[uid] = None #if the thread is dead, remove it from the dictionary
				testingThread = None
			return testingThread
		
	def _onClickedMainButton(self, button):
		'''
		Handle button clicks on id column. This can either start a test run, clear a prompt, or move from done state to idle state
		:param button: Button that was clicked on
		'''
		uid = button.id
		#The button is always bound. How it is treated depends on the meta state and whether the thread (if any) is waiting for a click
		testingThread = self._getActiveThread(uid)
		if testingThread:
			testingThread.processButtonClick() #maybe the thread has a prompt and wants to wake up
			return
		
		deviceUIInfo = self.deviceUIInfo[uid]
		deviceDescriptor = self.deviceDescriptors[uid]

		if deviceUIInfo.isDone(): #if currently in a PASS or FAIL state
			self._updateStateInfo({'uid': uid, 'state': PASSIVE_STATE, 'stateLabel': WAITING_TEXT, 'labelText': ' '}) #labelText cannot be "". It needs to be a space
			#TODO make yellow
			self.output = ""
			if not SKIP_IDLE_STATE:
				self._updateStateInfo({'uid': uid, 'state': IDLE_STATE, 'stateLabel': WAITING_TEXT, 'labelText': ' ', 'output': ' '}) #labelText cannot be "". It needs to be a space 
				return


		self._updateStateInfo({'uid':uid, 'state': ACTIVE_STATE, 'stateLabel': RUNNING_TEXT})	
		suite = self._loadSuite()
		testResult = TestResult()
		self.count += 1 #processing another one!
		
		testThread = TestingThread(suite, deviceDescriptor, self.count, self.mutexes, self.updateQueue, testResult) #reesult will get written to testResult
		self.testThreads[button.id] = testThread
		testThread.start() #start the thread, which will call runTestSuite

	#static
	_stateToColor ={PASS_STATE: SUCCESS_COLOR, FAIL_STATE:FAIL_COLOR, PROMPT_STATE: PROMPT_COLOR, ACTIVE_STATE:ACTIVE_COLOR, PAUSED_STATE:PAUSED_COLOR, IDLE_STATE: PASSIVE_COLOR}
	
	def _updateStateInfo(self, info):
		'''
		Kivy has threading issues if you try to update GUI components from a child thread.
		The solution is to add a @mainthread attribute to a function in the chlid class.
		This function will then run in the main thread. It, in turn, calls this method
		info.uid: The port
		info.metaState: Can set ACTIVE or IDLE, etc
		info.state: corresponds to the states. e.g. PASSIVE_STATE
		info.stateLabel: Text label for the state, such as RUNNING_TEXT
		info.labelText: The label for the test case that is being run
		info.progress: number value for progress bar
		info.output: The output for the test case
		info.prompt: Any prompt to show
		'''
		uid = info['uid']
		metaState = info.get('metaState')
		state = info.get('state')
		stateLabel = info.get('stateLabel')
		labelText = info.get('labelText')
		progress = info.get('progress')
		output = info.get('output')
		prompt = info.get('prompt')
		
		deviceUIInfo = self.deviceUIInfo[uid]
		widgetInfo = deviceUIInfo.widgetInfo
		
		if metaState:
			deviceUIInfo.metaState = metaState
			
		if stateLabel:
			widgetInfo['stateLabel'].text = stateLabel
										
		if labelText:
			widgetInfo['label'].text = labelText
			
		if progress:
			widgetInfo['progress'].value = progress
		
		if output:
			deviceUIInfo.output = output
			self._onShowOutput(None,uid) #if the output detail is showing this output, it will be updated
		
		if prompt:
			widgetInfo['label'].text = prompt
			
		if state:
			deviceUIInfo.state = state
			color = self._stateToColor[state]
			for widget in widgetInfo.itervalues():
				widget.color = color
		
	
	def _triggerUpdate(self):
		'''
		The KivyQueue will call this method every time something is added to the queue.
		'''
		self.kivyUpdateTrigger() #trigger the main kivy thread to look in the KivyQueue
		
	def _onUpdateTrigger(self,x):
		'''
		This method is called by Kivy's Clock object before the next frame when self.kivyUpdateTrigger() has been called
		'''
		while not self.updateQueue.empty(): #process everything in the queue
			info = self.updateQueue.get()
			self._updateStateInfo(info)


class KivyQueue(Queue):
	'''
	Modifed from comment here: http://stackoverflow.com/questions/22031262/altering-a-kivy-property-from-another-thread
    A Multithread safe class that calls a callback whenever an item is added
    to the queue. Instead of having to poll or wait, you could wait to get
    notified of additions.
    '''

	notify_func = None

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

if __name__ == '__main__':
	app = TestSuiteGUIApp("Flasher")
	try:
		app.run()
	except (KeyboardInterrupt, SystemExit):
		app.stop()

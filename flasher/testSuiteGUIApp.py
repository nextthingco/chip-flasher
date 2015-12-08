# -*- coding: utf-8 -*-
import threading
from kivy.config import Config

# Config.set('graphics', 'fullscreen', '1')
Config.set('graphics', 'width', '1024')
Config.set('graphics', 'height', '768')

from kivy.app import App
from kivy.clock import Clock
from persistentdata import PersistentData
from os import path
from deviceDescriptor import DeviceDescriptor
from progress import Progress
from testSuiteGUIView import *
import os

import subprocess
import unittest
from flasher import Flasher
from chipHardwareTest import ChipHardwareTest
from observable_test import *
from ui_strings import *
UDEV_RULES_FILE = '/etc/udev/rules.d/flasher.rules'

OSX_FONT="/Library/Fonts/Arial Unicode.ttf"
UBUNTU_FONT="/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf"
if os.path.isfile( OSX_FONT ):
	FONT_NAME = OSX_FONT
else:
	FONT_NAME = UBUNTU_FONT
	
	

log = LogManager.get_global_log()
get_class = lambda x: globals()[x]

META_STATE_IDLE = 0
META_STATE_ACTIVE = 1
META_STATE_DONE = 2	
SKIP_IDLE_STATE = True # If true, then there won't be an idle state between done and testing

class TestSuiteGUIApp( App ):
	'''
	The main application for a GUI-based, parallel test suite runner
	'''
	def __init__( self, testSuiteName ):
		super( TestSuiteGUIApp, self ).__init__()
		cwd = path.dirname( path.dirname( path.realpath( __file__ ) ) )
		self.testSuiteName = testSuiteName
		PersistentData.read()
		self.testThreads = {}
		self.metaStates = {}
		self.labelMap = {}
		self.deviceDescriptors, self.hubs = DeviceDescriptor.readRules(UDEV_RULES_FILE)
		self.mutexes = {}
		self.count = 0
		
	def _loadSuite(self):
		'''
		Loads the test suite to turn
		'''
		tl = unittest.TestLoader()
		suite = tl.loadTestsFromTestCase(get_class(self.testSuiteName))
		return suite
	
		
	def displayTitle( self ):
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
		self.title = "Host: " + self.hostname + " | Flasher Revision: " + self.rev[0:10] + " | Firmware Build: " + self.build_string


	def onShowOutput(self,button):
		if button.id in self.testThreads:
			thread = self.testThreads[button.id]
			thread.onShowOutput(button)

	def onRunTestSuite(self, button):
		
		#currently the button remains bound. we could also unbind it while running to ignore these messages
		if button in self.testThreads and self.testThreads[button.id].isAlive(): #check to see we are not currently testing for this button
			return
		
		if not button  in self.metaStates:
			self.metaStates[button] = META_STATE_IDLE
 		
		metaState = self.metaStates[button]
 		
		if metaState == META_STATE_ACTIVE: #ignore if currently running
			return
		self.count += 1
		deviceDescriptor = self.deviceDescriptors[button.id]

		if metaState == META_STATE_DONE:
			deviceDescriptor.setWidgetColor(PASSIVE_COLOR)
			deviceDescriptor.widgetInfo['status'].text=WAITING_TEXT
			deviceDescriptor.widgetInfo['label'].text=''
			self.output = ""
			self.setOutput("",deviceDescriptor)
			if not SKIP_IDLE_STATE:
				self.metaStates[button] = META_STATE_IDLE
				return

		self.metaStates[button] = META_STATE_ACTIVE
			
		suite = self._loadSuite()
		testThread = TestingThread(suite,self,button,deviceDescriptor,self.count) #, sel)
# 		testThread = threading.Thread( target=self._runTestSuite.__get__(self,TestSuiteGUIApp), args=(button,)) # The test must run in another thread so as not to block kivy
		self.testThreads[button.id] = testThread
		testThread.start() #start the thread, which will call runTestSuite
		
	def setOutput(self,text, deviceDescriptor):
		self.output = text
		print "setting output to: " + text + " for device " + deviceDescriptor.uid 
		self.view.setOutputContent(text, deviceDescriptor)
		
	def build( self ):
		self.rev = 0
		self.hostname = ""
		self.build_string = ""
		self.displayTitle()

		
		self.view = TestSuiteGUIView(deviceDescriptors=self.deviceDescriptors, hubs = self.hubs)
		
		for key in self.deviceDescriptors:
			deviceDescriptor = self.deviceDescriptors[key]
			deviceDescriptor.widgetInfo['button'].bind( on_press=self.onRunTestSuite.__get__(self, TestSuiteGUIApp))
			deviceDescriptor.widgetInfo['label'].bind( on_press=self.onShowOutput.__get__(self, TestSuiteGUIApp))


		return self.view

	def on_stop( self ):
# 		PersistentData.write()
# 		LogManager.close_all_logs()
		pass


class TestingThread(threading.Thread):
	def __init__(self, suite, flasherApp, promptButton, deviceDescriptor,count):
	 	threading.Thread.__init__(self)
	 	self.suite = suite
	 	self.flasherApp = flasherApp
		self.view = flasherApp.view
		self.promptButton = promptButton
		self.deviceDescriptor = deviceDescriptor
		self.widgetInfo = deviceDescriptor.widgetInfo
		self.label = deviceDescriptor.widgetInfo['label']
		self.count = count
		
		self.button =  deviceDescriptor.widgetInfo['button']
		self.uid = self.button.id
		self.totalProgressBar = deviceDescriptor.widgetInfo['totalProgressBar']
		self.status = deviceDescriptor.widgetInfo['status']

		self.testCaseAttributes = {'deviceDescriptor': deviceDescriptor} #such as for the flasher to get the port
		
		self.totalProgressSeconds = sum( progressForTest(testCase) for testCase in suite)
		self.output = ""
			
	def onShowOutput(self,label):
		self.view.showOutputOfPort(self.deviceDescriptor)
		self.setOutput(self.output)

	def setOutput(self,text):
		self.flasherApp.setOutput(text,self.deviceDescriptor)
			
	def run(self):
		self._runTestSuite()
		
	def _runTestSuite(self):
		stateInfoCallback = self.onStateChange.__get__(self, TestingThread) #Register the view for state changes
 		progressCallback = self.onProgressChange.__get__(self,TestingThread) #this progress is not used
		for testCase in self.suite:
			decorateTest(testCase, stateInfoObservers = [stateInfoCallback], progressObservers = [progressCallback], attributes = self.testCaseAttributes ) #Decorate the test cases to add the callback observer and logging above
		self._setColor(PASSIVE_COLOR)
		result = unittest.TextTestRunner(verbosity=2, failfast=True).run(self.suite) # This runs the whole suite of tests. For now, using TextTestRunner
		ok = len(result.errors) == 0 # Any errors?
		if ok:
			self.testsPassed()
		else:
			self.testsFailed()
		self.flasherApp.metaStates[self.button] = META_STATE_DONE	
	def _setColor(self,color):	
		self.deviceDescriptor.setWidgetColor(color)
		
		
	def onStateChange(self,stateInfo):
		method = stateInfo['method']
		testCase = stateInfo['testCase']
		self.label.text = stateInfo['label']
		englishName = stateInfo['label'].split('\n')[0]

		label = self.label
		if label:
			prompt = None
			if stateInfo['when']== "before":
				self.output += (str(self.count) + ": BEFORE: " + englishName + " device: "+ self.deviceDescriptor.textForLog())

				self.setOutput(self.output)
				testCase.output=""
				self.progress = None
				self.totalProgressBar.value = 0
				self.totalProgressBar.max = 1

				prompt = promptBeforeForTest(testCase)
			else:
				prompt = promptAfterForTest(testCase)
			if prompt:
				self.button.bind( on_press=self.onWakeup.__get__(self, TestingThread)) #listen to button 
				self.event = threading.Event()
				self._setColor(PROMPT_COLOR)
				self.status.text = prompt
				self.event.wait()
					
			progressSeconds =  progressForTest(testCase)
			timeout =  timeoutForTest(testCase)
			lock = None
			mutex = mutexForTest(testCase)
			if stateInfo['when']== "before":
				if mutex: #if this test needs a mutex as indicated in the test suite
					if not mutex in self.flasherApp.mutexes:
						self.flasherApp.mutexes[mutex] = threading.Lock() #make a new one
					lock = self.flasherApp.mutexes[mutex] #get the lock
					self._setColor(PASSIVE_COLOR)
					self.status.text = PAUSED_TEXT
					lock.acquire()

				self._setColor(ACTIVE_COLOR)
				if progressSeconds:
					self.progress = Progress(progressObservers = [self.onProgressChange.__get__(self,TestingThread)], finish=progressSeconds, timeout = timeout )
			else: #after
				if mutex: # @mutex is an annotation defined in observable_test
					self.flasherApp.mutexes[mutex].release()
				if progressSeconds:
					progressCallback = self.progress.addProgress.__get__(progress, Progress)
					Clock.unschedule(progressCallback)
					
				self.output += testCase.output
				self.output += (str(self.count) + ": AFTER: " + englishName + " device: "+ self.deviceDescriptor.textForLog() + " time: " + str(stateInfo['executionTime']))
				self.setOutput(self.output)
				self._setColor(PASSIVE_COLOR)

 			self.status.text = TESTING_TEXT

	def onWakeup(self,widget):
		self.event.set()
		widget.unbind( on_press=self.onWakeup.__get__(self, TestingThread))
		pass
	
	def testsPassed(self):
		self._setColor(SUCCESS_COLOR)
		self.label.text=""
		self.status.text =  PASS_TEXT

	def testsFailed(self):
		print self.output
		self._setColor(FAIL_COLOR)
		self.status.text = FAIL_TEXT
	
	def onProgressChange(self,progress):
		self.totalProgressBar.value = progress

if __name__ == '__main__':
	app = TestSuiteGUIApp("Flasher")
	try:
		app.run()
	except (KeyboardInterrupt, SystemExit):
		app.stop()

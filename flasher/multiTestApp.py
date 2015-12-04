# -*- coding: utf-8 -*-
import threading
from kivy.config import Config

# Config.set('graphics', 'fullscreen', '1')

from kivy.app import App
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.progressbar import ProgressBar
from kivy.uix.textinput import TextInput
from kivy.uix.boxlayout import BoxLayout
from kivy.core.window import Window
from kivy.clock import Clock
from persistentdata import PersistentData
from logmanager import LogManager
from os import path
from collections import OrderedDict

import re
from observable_test import *
from progress import Progress
import os

import sys
import subprocess
import unittest
from flashTest import Upload
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from hwtest import FactoryHardwareTest

UDEV_RULES_FILE = '/etc/udev/rules.d/flasher.rules'

OSX_FONT="/Library/Fonts/Arial Unicode.ttf"
UBUNTU_FONT="/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf"
if os.path.isfile( OSX_FONT ):
	FONT_NAME = OSX_FONT
else:
	FONT_NAME = UBUNTU_FONT
	
WAITING_TEXT="Waiting\n等候"
PAUSED_TEXT="Paused\n暂停"

TESTING_TEXT="Testing\n测试"
FINSHED_TEXT="Finished\n完"
	
UDEV_REGEX = re.compile(ur'.*KERNELS.*\"(.*)\".*ATTR\{idVendor}.*\"(.*)\".*ATTRS\{idProduct\}.*\"(.*)\".*SYMLINK.*\"(.*)\"')

log = LogManager.get_global_log()

class FlasherScreen( GridLayout ):
	successColor = [ 1, 0, 0, 1] # in China RED is positive
	failColor = [ 1, 1, 1, 1] # in China, WHITE is negative
	activeColor = [ 0, 1, 0, 1] # we will use GREEN for active
	passiveColor = [ 1, 1, 0, 1] # we will use YELLOW for passive
	promptColor = [ 1, .4, .3, 1] # we will use YELLOW for passive

# 	deviceRowMap = {}
		
	def __init__( self, **kwargs ):
		super(FlasherScreen, self).__init__(**kwargs)
		self.deviceDescriptors = kwargs['deviceDescriptors']
		
		self.keyboard = Window.request_keyboard( self.keyboard_closed, self )
		self.keyboard.bind( on_key_down=self.on_keyboard_down )
		self.keyboard.bind( on_key_up=self.on_keyboard_up )
		
		
		self.cols = 4 # columns for this grid layout

		
		#make the table by looping through devices
		for key in self.deviceDescriptors:
			deviceDescriptor = self.deviceDescriptors[key]
			
			self.addDeviceWidget(deviceDescriptor,key,'button',
						Button(text=deviceDescriptor.portNumber(), color = self.passiveColor, font_size=76, font_name=FONT_NAME, halign="center", size_hint_x=None, width=200))

			self.addDeviceWidget(deviceDescriptor,key,'status',
						Label( text = WAITING_TEXT, color = self.passiveColor, font_size=30, font_name=FONT_NAME, halign="center" ))
			
			# The testing state. Perhaps add a totalProgress bar here?
			self.addDeviceWidget(deviceDescriptor,key,'label',
						Label( text = '', color = self.passiveColor, font_size = 30, font_name=FONT_NAME, halign="center" ))
			
			self.addDeviceWidget(deviceDescriptor,key,'totalProgressBar',
						ProgressBar(value=0, max=100, size_hint=(1, 1.0/15) ))
	
	def addDeviceWidget(self,deviceDescriptor,key,name,widget):
		widget.id = key
		deviceDescriptor.widgetInfo[name] = widget
		self.add_widget(widget)
		
	def keyboard_closed( self ):
		self.keyboard.unbind( on_key_down=self._on_keyboard_down )
		self.keyboard.unbind( on_key_up=self.on_keyboard_up )
		self.keyboard = None

	def on_keyboard_down( self, keyboard, keycode, text, modifiers ):
		root = BoxLayout()
		if keycode[1] == '1':
			self.children[0].background_color=[1,0,0,1]
		return True

	def on_keyboard_up( self, keyboard, keycode ):
		root = BoxLayout()
		if keycode[1] == '1':
			self.children[0].background_color=[ 0, 1, 0, 1 ]
		return True
	

	def get_widget(self):
		return self.widget

    
def loggerTest(stateInfo):
		print "LOG observed " + stateInfo['when'] + " " + stateInfo['method'] + " label: " + stateInfo['label']

get_class = lambda x: globals()[x]


def readRules(rulesFilePath):
	'''
	Parse a udev file and construct a map of descriptors which map fel, fastboot, and serial-gadget to a physical port
	There are other, maybe better approaches to this, for example, running udevadm info -e
	and parsing that result for the appropriate devices
	:param rulesFilePath:
	'''
	descriptorMap = OrderedDict() #preserve order from udev file
	with open(rulesFilePath, 'r') as rulesFile:
		for line in rulesFile:
			match = UDEV_REGEX.match(line)
			if match:
				port = match.group(1)
				vendor = match.group(2)
				product = match.group(3)
				symlink = match.group(4)
				if port in descriptorMap:
					descriptor = descriptorMap[port]
				else:
					descriptor = DeviceDescriptor(port,vendor,product)
					descriptorMap[port] = descriptor
				device = '/dev/' + symlink	
				if vendor == '1f3a' and product == 'efe8':
					descriptor.fel = device
				elif vendor == '18d1' and product == '1010':
					descriptor.fastboot = device
				elif vendor == "0525" and product == 'a4a7':
					descriptor.serialGadget = device
					
	return descriptorMap

class DeviceDescriptor:
	def __init__(self,port,vendor,product):
		self.port = port
		self.vendor = vendor
		self.product = product
		self.fel = None
		self.fastboot = None
		self.widgetInfo = {}
		
	def setWidgetColor(self,color):
		for widget in self.widgetInfo.itervalues():
			widget.color = color
	
	def portNumber(self):
		return self.port.split('.')[-1] #last value after .
	

META_STATE_IDLE = 0
META_STATE_ACTIVE = 1
META_STATE_DONE = 2	

class FlasherApp( App ):
	def __init__( self, testSuiteName ):
		super( FlasherApp, self ).__init__()
		cwd = path.dirname( path.dirname( path.realpath( __file__ ) ) )
		self.testSuiteName = testSuiteName
		PersistentData.read()
		self.testThreads = {}
		self.metaStates = {}
		self.labelMap = {}
		self.deviceDescriptors = readRules(UDEV_RULES_FILE)
		self.mutexes = {}

		
	def _loadSuite(self):
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


	
	def onRunTestSuite(self, button):
		
		#currently the button remains bound. we could also unbind it while running to ignore these messages
		if button in self.testThreads and self.testThreads[button].isAlive(): #check to see we are not currently testing for this button
# 			print "already testing"
			return
		
		if not button  in self.metaStates:
			self.metaStates[button] = META_STATE_IDLE
 		
		metaState = self.metaStates[button]
 		
		if metaState == META_STATE_ACTIVE: #ignore if currently running
			return
		
		deviceDescriptor = self.deviceDescriptors[button.id]

		if metaState == META_STATE_DONE:
			deviceDescriptor.setWidgetColor(self.screen.passiveColor)
			deviceDescriptor.widgetInfo['status'].text=WAITING_TEXT
			deviceDescriptor.widgetInfo['label'].text=''

			self.metaStates[button] = META_STATE_IDLE
			return
		elif metaState == META_STATE_IDLE:
			self.metaStates[button] = META_STATE_ACTIVE
			
		suite = self._loadSuite()
		testThread = TestingThread(suite,self,button,deviceDescriptor) #, sel)
# 		testThread = threading.Thread( target=self._runTestSuite.__get__(self,FlasherApp), args=(button,)) # The test must run in another thread so as not to block kivy
		self.testThreads[button] = testThread
		testThread.start() #start the thread, which will call runTestSuite
		
		
		
	def build( self ):
		self.rev = 0
		self.hostname = ""
		self.build_string = ""
		self.displayTitle()
		Config.set('graphics', 'fullscreen', '1')

# 		Config.set('graphics', 'width', '1200')
# 		Config.set('graphics', 'height', '800')
		
		self.screen = FlasherScreen(deviceDescriptors=self.deviceDescriptors)
		
		for key in self.deviceDescriptors:
			deviceDescriptor = self.deviceDescriptors[key]
			deviceDescriptor.widgetInfo['button'].bind( on_press=self.onRunTestSuite.__get__(self, FlasherApp))

		return self.screen

	def on_stop( self ):
# 		PersistentData.write()
# 		LogManager.close_all_logs()
		pass

		
class TestingThread(threading.Thread):
	def __init__(self, suite, flasherApp, promptButton, deviceDescriptor):
	 	threading.Thread.__init__(self)
	 	self.suite = suite
	 	self.flasherApp = flasherApp
		self.screen = flasherApp.screen
		self.promptButton = promptButton
		self.deviceDescriptor = deviceDescriptor
		self.widgetInfo = deviceDescriptor.widgetInfo
		self.label = deviceDescriptor.widgetInfo['label']
		self.button =  deviceDescriptor.widgetInfo['button']
		self.totalProgressBar = deviceDescriptor.widgetInfo['totalProgressBar']
		self.status = deviceDescriptor.widgetInfo['status']

		self.testCaseAttributes = {'deviceDescriptor': deviceDescriptor} #such as for the flasher to get the port
		
		self.totalProgressSeconds = sum( progressForTest(testCase) for testCase in suite)
# 		print self.totalProgressSeconds	
		
	def run(self):
		self._runTestSuite()
		
	def _runTestSuite(self):
		stateInfoCallback = self.onStateChange.__get__(self, TestingThread) #Register the screen for state changes
 		progressCallback = self.onProgressChange.__get__(self,TestingThread) #this progress is not used
		for testCase in self.suite:
			decorateTest(testCase, stateInfoObservers = [stateInfoCallback], progressObservers = [progressCallback], attributes = self.testCaseAttributes ) #Decorate the test cases to add the callback observer and logging above
		self._setColor(self.screen.passiveColor)
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
		label = self.label
		if label:
			prompt = None
			if stateInfo['when']== "before":
				self.progress = None
				self.totalProgressBar.value = 0
				self.totalProgressBar.max = 1

				prompt = promptBeforeForTest(testCase)
			else:
				prompt = promptAfterForTest(testCase)
			if prompt:
				self.button.bind( on_press=self.onWakeup.__get__(self, TestingThread)) #listen to button 
				self.event = threading.Event()
				self._setColor(self.screen.promptColor)
				self.status.text = prompt
				self.event.wait()
					
			progressSeconds =  progressForTest(testCase)
			timeout =  timeoutForTest(testCase)
			lock = None
			mutex = mutexForTest(testCase)
			if stateInfo['when']== "before":
				if mutex: #if this test needs a mutex
					if not mutex in self.flasherApp.mutexes:
						self.flasherApp.mutexes[mutex] = threading.Lock() #make a new one
					lock = self.flasherApp.mutexes[mutex] #get the lock
					self._setColor(self.screen.passiveColor)
					self.status.text = PAUSED_TEXT
					lock.acquire()

				self._setColor(self.screen.activeColor)
				if progressSeconds:
					self.progress = Progress(progressObservers = [self.onProgressChange.__get__(self,TestingThread)], finish=progressSeconds, timeout = timeout )
			else: #after
				if mutex:
					self.flasherApp.mutexes[mutex].release()
				if progressSeconds:
					progressCallback = self.progress.addProgress.__get__(progress, Progress)
					Clock.unschedule(progressCallback)
				self._setColor(self.screen.passiveColor)

 			self.label.text = stateInfo['label']
 			self.status.text = TESTING_TEXT
#  			self.button.color = self.screen.activeColor

	def onWakeup(self,widget):
		self.event.set()
		widget.unbind( on_press=self.onWakeup.__get__(self, TestingThread))
		pass
	
	def testsPassed(self):
		self._setColor(self.screen.successColor)
		self.label.text=""
		self.status.text = "PASS\n通过"

	def testsFailed(self):
		self._setColor(self.screen.failColor)
		self.status.text = "FAIL\n失败"
	
	def onProgressChange(self,progress):
		self.totalProgressBar.value = progress
# 		self.totalProgressBar.max = 1
# 
# # 		value = progress * 100
# 		self.screen.set_progress(progress * 100)

if __name__ == '__main__':
# 	dd = readRules('./multi_udev.rules')
# 	print dd
	app = FlasherApp("Upload")
	try:
		app.run()
	except (KeyboardInterrupt, SystemExit):
		app.stop()

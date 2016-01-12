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
from observable_test import *
from progress import Progress
import os

import sys
import subprocess
import unittest
from flasher import Flasher
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from hwtest import FactoryHardwareTest
OSX_FONT="/Library/Fonts/Arial Unicode.ttf"
UBUNTU_FONT="/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf"
if os.path.isfile( OSX_FONT ):
	FONT_NAME = OSX_FONT
else:
	FONT_NAME = UBUNTU_FONT

log = LogManager.get_global_log()

class FlasherScreen( GridLayout ):
	SUCCESS_COLOR = [ 1, 0, 0, 1] # in China RED is positive
	FAIL_COLOR = [ 1, 1, 1, 1] # in China, WHITE is negative
	ACTIVE_COLOR = [ 0, 1, 0, 1] # we will use GREEN for active
	PASSIVE_COLOR = [ 1, 1, 0, 1] # we will use YELLOW for passive

	def __init__( self, **kwargs ):
		super(FlasherScreen, self).__init__(**kwargs)
		self.keyboard = Window.request_keyboard( self.keyboard_closed, self )
		self.keyboard.bind( on_key_down=self.on_keyboard_down )
		self.keyboard.bind( on_key_up=self.on_keyboard_up )
		self.cols = 2
		self.widget = GridLayout( cols=2 )
		self.innergrid = GridLayout( cols=1 )
		self.listview = GridLayout( cols=1, size_hint=(0.25, 1) ) #ListView( size_hint=(1, 2), item_strings=[ str(key) for key,value in fsm.iteritems() ])
	
		
		
		self.widget.add_widget( self.listview )
		self.widget.add_widget( self.innergrid )
		self.button = Button(text="waiting", font_size=76, font_name=FONT_NAME, halign="center")
		self.button.id = "port1"
		self.innergrid.add_widget( self.button )

		self.progressbar = ProgressBar(value=0, max=100, size_hint=(1, 1.0/15) )
		self.innergrid.add_widget( self.progressbar )
		self.add_widget(self.widget)
		
	def addTestToListView(self,label):
		self.listview.add_widget(label)
	
		
		
	def instanceInit(self):
		pass

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
	
	def onStateChange(self,stateInfo):
		if stateInfo['label']:
			self.button.text = stateInfo['label']
			self.button.color = self.ACTIVE_COLOR

	def set_progress(self, value, max=100 ):
		self.progressbar.value = value*100.0
		self.progressbar.max = max*100.0

	def get_progress( self ):
		return { "value": self.progressbar.value / 100.0, "max": self.progressbar.max / 100.0 }

	def get_widget(self):
		return self.widget

    
def loggerTest(stateInfo):
		print "LOG observed " + stateInfo['when'] + " " + stateInfo['method'] + " label: " + stateInfo['label']

get_class = lambda x: globals()[x]

class TestSuiteGUIApp( App ):
	def __init__( self, testSuiteName ):
		super( TestSuiteGUIApp, self ).__init__()
		cwd = path.dirname( path.dirname( path.realpath( __file__ ) ) )
		self.testSuiteName = testSuiteName
		PersistentData.read()
		self.testThreads = {}
		self.labelMap = {}
		self.devices=["/dev/chip_usb"]
	
	def _loadSuite(self):
		tl = unittest.TestLoader()
		suite = tl.loadTestsFromTestCase(get_class(self.testSuiteName))
		return suite
	
	def displayTests(self):
		labels = []
# 		labels.append(Label( text='idle', font_name=FONT_NAME, halign="center" ))

		suite = self._loadSuite()
		for test in suite:
			text = labelForTest(test)
			if text:
				label = Label( text = labelForTest(test), color = self.screen.PASSIVE_COLOR, font_name=FONT_NAME, halign="center" )
				labels.append(label)
				self.labelMap[methodForTest(test)] = label
		
# 		labels.append(Label( text='pass', font_name=FONT_NAME, halign="center" ))
# 		labels.append(Label( text='fail', font_name=FONT_NAME, halign="center" ))
		for label in labels:
			self.screen.addTestToListView(label)


		
	def _displayTitle( self ):
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
		if button in self.testThreads and self.testThreads[button].isAlive(): #check to see we are not currently testing for this button
# 			print "already testing"
			return
		suite = self._loadSuite()
		testThread = TestingThread(suite,self,button)
# 		testThread = threading.Thread( target=self._runTestSuite.__get__(self,TestSuiteGUIApp), args=(button,)) # The test must run in another thread so as not to block kivy
		self.testThreads[button] = testThread
		testThread.start() #start the thread, which will call runTestSuite
		
		
		
	def build( self ):
		self.rev = 0
		self.hostname = ""
		self.build_string = ""
		self._displayTitle()
		self.screen = FlasherScreen()
		
		self.displayTests()
		button = self.screen.button
		self.screen.button.bind( on_press=self.onRunTestSuite.__get__(self, TestSuiteGUIApp))

		return self.screen

	def on_stop( self ):
# 		PersistentData.write()
# 		LogManager.close_all_logs()
		pass

		
class TestingThread(threading.Thread):
	def __init__(self, suite, flasherApp, promptButton):
	 	threading.Thread.__init__(self)
	 	self.suite = suite
	 	self.flasherApp = flasherApp
		self.screen = flasherApp.screen
		self.promptButton = promptButton
		
	def run(self):
		self._runTestSuite()
	def _runTestSuite(self):
		stateInfoCallback = self.onStateChange.__get__(self, TestingThread) #Register the screen for state changes
 		progressCallback = self.onProgressChange.__get__(self,TestingThread) #this progress is not used
		for testCase in self.suite:
			decorateTest(testCase, stateInfoObservers = [stateInfoCallback], progressObservers = [progressCallback] ) #Decorate the test cases to add the callback observer and logging above
		
		result = unittest.TextTestRunner(verbosity=2, failfast=True).run(self.suite) # This runs the whole suite of tests. For now, using TextTestRunner
		ok = len(result.errors) == 0 # Any errors?
		if ok:
			self.testsPassed()
		else:
			self.testsFailed()
		
	def onStateChange(self,stateInfo):
		method = stateInfo['method']
		testCase = stateInfo['testCase']
		# update the color of the label assocated with this test
# 		if testCase.stateNames and method in testCase.stateNames:
		label = self.flasherApp.labelMap.get(method,None)
		if label:
			prompt = None
			self.currentLabel = label
			if stateInfo['when']== "before":
				self.progress = None
				self.screen.set_progress(0, 100)
				prompt = promptBeforeForTest(testCase)
			else:
				prompt = promptAfterForTest(testCase)
			if prompt:
				self.screen.button.bind( on_press=self.onWakeup.__get__(self, TestingThread)) #listen to button 
				self.event = threading.Event()
				self.screen.button.text = prompt
				self.event.wait()
					
			progressSeconds =  progressForTest(testCase)
			timeout =  timeoutForTest(testCase)
			if stateInfo['when']== "before":
				label.color = self.screen.ACTIVE_COLOR
				if progressSeconds:
					self.progress = Progress(progressObservers = [self.onProgressChange.__get__(self,TestingThread)], finish=progressSeconds, timeout = timeout )
			else: #after
				if progressSeconds:
					progressCallback = self.progress.addProgress.__get__(progress, Progress)
					Clock.unschedule(progressCallback)

				label.color = self.screen.PASSIVE_COLOR
			self.screen.onStateChange(stateInfo)

	def onWakeup(self,button):
		self.event.set()
		self.screen.button.unbind( on_press=self.onWakeup.__get__(self, TestingThread))
		pass
	
	def testsPassed(self):
		self.screen.button.color = self.screen.SUCCESS_COLOR
		self.screen.button.text = "PASS\n通过"

	def testsFailed(self):
		self.screen.button.color = self.screen.FAIL_COLOR
		self.currentLabel.color = self.screen.FAIL_COLOR #last test failed
		self.screen.button.text = "FAIL\n失败"
	
	def onProgressChange(self,progress):
# 		value = progress * 100
		self.screen.set_progress(progress * 100)

if __name__ == '__main__':
	app = TestSuiteGUIApp("Flasher")
	try:
		app.run()
	except (KeyboardInterrupt, SystemExit):
		app.stop()
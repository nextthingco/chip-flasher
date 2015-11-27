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
from flasher.instance import Instance
from flasher import states
from flasher.fsm import FSM
from flasher.persistentdata import PersistentData
from flasher.logmanager import LogManager
from os import path
from observable_test import *
import os

import sys
import subprocess
import unittest
from flashTest import Upload
from hwtest import HardwareTest
from kivy.uix.label import Label

OSX_FONT="/Library/Fonts/Arial Unicode.ttf"
UBUNTU_FONT="/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf"
if os.path.isfile( OSX_FONT ):
	FONT_NAME = OSX_FONT
else:
	FONT_NAME = UBUNTU_FONT

log = LogManager.get_global_log()

class FlasherScreen( GridLayout ):
	successColor = [ 1, 0, 0, 1] # in China RED is positive
	failColor = [ 1, 1, 1, 1] # in China, WHITE is negative
	activeColor = [ 0, 1, 0, 1] # we will use GREEN for active
	passiveColor = [ 1, 1, 0, 1] # we will use YELLOW for passive

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
		self.button.text = stateInfo['label']
		self.button.color = self.activeColor

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

class FlasherApp( App ):
	def __init__( self, testSuiteName ):
		super( FlasherApp, self ).__init__()
		cwd = path.dirname( path.dirname( path.realpath( __file__ ) ) )
		self.testSuiteName = testSuiteName
		PersistentData.read()
		self.testThreads = {}
		self.labelMap = {}
	
	def _loadSuite(self):
		tl = unittest.TestLoader()
		suite = tl.loadTestsFromTestCase(get_class(self.testSuiteName))
		return suite
	
	def displayTests(self):
		labels = []
# 		labels.append(Label( text='idle', font_name=FONT_NAME, halign="center" ))

		suite = self._loadSuite()
		for test in suite:
			label = Label( text = labelForTest(test), color = self.screen.passiveColor, font_name=FONT_NAME, halign="center" )
			labels.append(label)
			self.labelMap[methodForTest(test)] = label
		
# 		labels.append(Label( text='pass', font_name=FONT_NAME, halign="center" ))
# 		labels.append(Label( text='fail', font_name=FONT_NAME, halign="center" ))
		for label in labels:
			self.screen.addTestToListView(label)


		
	def update_title( self, dt ):
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

	def testsPassed(self):
		self.screen.button.color = self.screen.successColor
		self.screen.button.text = "PASS\n通过"

	def testsFailed(self):
		self.screen.button.color = self.screen.failColor
		self.screen.button.text = "FAIL\n失败"

	
	def onRunTestSuite(self, button):
		if button in self.testThreads and self.testThreads[button].isAlive(): #check to see we are not currently testing for this button
			print "already testing"
			return
		testThread = threading.Thread( target=self._runTestSuite.__get__(self,FlasherApp) ) # The test must run in another thread so as not to block kivy
		self.testThreads[button] = testThread
		testThread.start() #start the thread, which will call runTestSuite
		
	def onStateChange(self,stateInfo):
		method = stateInfo['method']
		testCase = stateInfo['testCase']
		# update the color of the label assocated with this test
# 		if testCase.stateNames and method in testCase.stateNames:
		label = self.labelMap[method]
		if stateInfo['when']== "before":
			label.color = self.screen.activeColor
# Not working yet				
# 				progressSeconds =  progressForTest(testCase)
# 				if progressSeconds:
# 					progress = Progress(progressObservers = [self.onProgressChange.__get__(self,FlasherApp)])
# 					Clock.schedule_interval(progress.addProgress.__get__(progress, Progress), 1.0/progressSeconds ) # callback for bound method
		else:
			label.color = self.screen.passiveColor
		self.screen.onStateChange(stateInfo)
	
	def onProgressChange(self,progress):
		value = progress * 100
		self.screen.set_progress(value)
		
	def _runTestSuite(self):
		suite = self._loadSuite()
		stateInfoCallback = self.onStateChange.__get__(self, FlasherApp) #Register the screen for state changes
		progressCallback = self.onProgressChange.__get__(self,FlasherApp)
		for testCase in suite:
			decorateTest(testCase,stateInfoObservers = [stateInfoCallback], progressObservers = [progressCallback] ) #Decorate the test cases to add the callback observer and logging above
		
		result = unittest.TextTestRunner(verbosity=2, failfast=True).run(suite) # This runs the whole suite of tests. For now, using TextTestRunner
		ok = len(result.errors) == 0 # Any errors?
		if ok:
			self.testsPassed()
		else:
			self.testsFailed()
		
	def build( self ):
		self.rev = 0
		self.hostname = ""
		self.build_string = ""

		Clock.schedule_interval( self.update_title, 0.5 )
# 		if self.fsm_implementation in FSM.fsm:
# 			FSM.set_implementation( self.fsm_implementation )
		self.screen = FlasherScreen()
# 		self.loadSuite()
		
		self.displayTests()
		self.screen.button.bind( on_press=self.onRunTestSuite.__get__(self, FlasherApp))

# 		self.runSuite()
		return self.screen

	def on_stop( self ):
		states.stop()
		PersistentData.write()
		LogManager.close_all_logs()
		

if __name__ == '__main__':
	app = FlasherApp("Upload")
	try:
		app.run()
	except (KeyboardInterrupt, SystemExit):
		app.stop()

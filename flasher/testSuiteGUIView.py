# -*- coding: utf-8 -*-
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.progressbar import ProgressBar
from kivy.uix.boxlayout import BoxLayout
from kivy.core.window import Window
from kivy.uix.behaviors import ButtonBehavior
from kivy.graphics import Color
from logmanager import LogManager

import os

from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.splitter import Splitter

from deviceDescriptor import DeviceDescriptor
from ui_strings import *

OSX_FONT="/Library/Fonts/Arial Unicode.ttf"
UBUNTU_FONT="/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf"
if os.path.isfile( OSX_FONT ):
	FONT_NAME = OSX_FONT
else:
	FONT_NAME = UBUNTU_FONT
	

log = LogManager.get_global_log()


HUBS_IN_COLUMNS = True # if True, there will be one visual column per hub as defined by the UDEV entry: chip-id-hub-mode
SHOW_STATUS = True # if True, shows an Idle.., Testing,  Pass/Fail column


SUCCESS_COLOR = [ 0, 1, 0, 1] # GREEN
FAIL_COLOR = [ 1, 0, 0, 1] # RED
ACTIVE_COLOR = [ 1, 1, 1, 1] # we will use WHITE for active
PASSIVE_COLOR = [ 1, 1, 0, 1] # we will use YELLOW for passive
PROMPT_COLOR = [ 1, .4, .3, 1] # we will use ORANGE for prompts
WHITE_COLOR = [ 1, 1, 1, 1] # in China, WHITE is negative
YELLOW_COLOR = [ 1, 1, 0, 1] # in China, WHITE is negative
PAUSED_COLOR = [ 1, .5, 0, 1] # in China, WHITE is negative

class LabelButton(ButtonBehavior, Label):
	'''
	This is a mixin which will add the ability to receive push events from a label. No code needed
	'''
	pass
   
class TestSuiteGUIView( BoxLayout ):

	def __init__( self, **kwargs ):
		super(TestSuiteGUIView, self).__init__(**kwargs)
		self.deviceDescriptors = kwargs['deviceDescriptors']
		self.hubs = kwargs['hubs']
# 		self.keyboard = Window.request_keyboard( self.keyboard_closed, self )
# 		self.keyboard.bind( on_key_down=self.on_keyboard_down )
# 		self.keyboard.bind( on_key_up=self.on_keyboard_up )

		outputView = BoxLayout(orientation='vertical') #the right half of the splitter
		self.outputTitle = Label(text="", font_size=20, color=YELLOW_COLOR,  size_hint=(1, .1))
		outputView.add_widget(self.outputTitle) #add in a title
						
		outputBodyView = ScrollView(scroll_y = 1) #the body will scroll
		self.output = Label(text="", valign = "top", font_size=16, size_hint=(1, None))
		zzz= GridLayout(cols = 1, size_hint_y = None)
		zzz.add_widget(self.output)
		outputBodyView.add_widget(zzz)
		
		outputView.add_widget(outputBodyView)
		
		splitter = 	Splitter(sizable_from = 'left', min_size = 10, max_size = 600,size_hint=(.05, 1))
		
		rows = len(self.deviceDescriptors)
		
		rowSizeFactor = 2 # 14.0 / rows #adjust font size according to number of rows
# 		rowSizeFactor = min(rowSizeFactor,15)
		if HUBS_IN_COLUMNS:
			hubColumns = len(self.hubs)
		else:
			hubColumns = 1

		if HUBS_IN_COLUMNS:
			rowSizeFactor *= hubColumns
		
		hubPanels= GridLayout(cols=hubColumns)

		cols = 3
		if not SHOW_STATUS:
			cols = cols-1
		self.deviceDescriptors
		for i,hub in enumerate(self.hubs):
			testingView = GridLayout(cols=cols ,size_hint=(.95, 1))
			hubPanels.add_widget(testingView)
			addTo = testingView #add these to the py grid view. If we want to have many columns, this would add to a sub grid
			for key, deviceDescriptor in self.deviceDescriptors.iteritems():
				if deviceDescriptor.hub != hub:
					continue
				self.addDeviceWidget(addTo, deviceDescriptor,key,'button',
							Button(text=deviceDescriptor.uid, color = PASSIVE_COLOR, font_size=30 * rowSizeFactor, font_name=FONT_NAME, halign="center", size_hint_x=None, width=100))

				if SHOW_STATUS: # global option whether to display the status 
					statusAddTo = addTo
				else:
					statusAddTo = None # the widget is created as an orphan. It needs to exists because other code will try to update it
				self.addDeviceWidget(statusAddTo, deviceDescriptor,key,'status',
								Label( text = WAITING_TEXT, color = PASSIVE_COLOR, font_size=13 * rowSizeFactor, font_name=FONT_NAME, halign="center", size_hint_x=None, width=90 ))
				
				#The label column consists of both text and a progress bar positioned inside a box layout
				stateBox = BoxLayout(orientation='vertical')
				self.addDeviceWidget(stateBox, deviceDescriptor,key,'label',
							LabelButton( text = '', color = PASSIVE_COLOR, font_size=12 * rowSizeFactor, font_name=FONT_NAME, halign="center" ))
			
				self.addDeviceWidget(stateBox, deviceDescriptor,key,'totalProgressBar',
							ProgressBar(value=0, max=100, halign="center",size_hint=(.9, 1.0/15) ))
				
				addTo.add_widget(stateBox)
				self.addDeviceWidget(None, deviceDescriptor,key,'output',
							LabelButton( text = '', color = WHITE_COLOR, font_size = 10, font_name=FONT_NAME, halign="left" ))
				

		splitter.add_widget(outputView)	
		self.add_widget(hubPanels)
		self.add_widget(splitter)
		
		self.showingOutputOfPort = None
	
	
	def setOutputContent(self,text, deviceDescriptor):
		if deviceDescriptor == self.showingOutputOfPort:
# 			self.outputTitle.text=deviceDescriptor.port
			self.output.text = text
	
	def showOutputOfPort(self,deviceDescriptor):
		self.showingOutputOfPort = deviceDescriptor
		self.outputTitle.text=deviceDescriptor.textForLog()
		
	def addDeviceWidget(self,addTo, deviceDescriptor,key,name,widget):
		widget.id = key
		deviceDescriptor.widgetInfo[name] = widget
		if addTo:
			addTo.add_widget(widget)
		return widget
		
# 	def keyboard_closed( self ):
# 		self.keyboard.unbind( on_key_down=self._on_keyboard_down )
# 		self.keyboard.unbind( on_key_up=self.on_keyboard_up )
# 		self.keyboard = None
# 
# 	def on_keyboard_down( self, keyboard, keycode, text, modifiers ):
# 		root = BoxLayout()
# 		if keycode[1] == '1':
# 			self.children[0].background_color=[1,0,0,1]
# 		return True
# 
# 	def on_keyboard_up( self, keyboard, keycode ):
# 		root = BoxLayout()
# 		if keycode[1] == '1':
# 			self.children[0].background_color=[ 0, 1, 0, 1 ]
# 		return True
	

	def get_widget(self):
		return self.widget

    
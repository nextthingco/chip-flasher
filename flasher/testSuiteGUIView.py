# -*- coding: utf-8 -*-
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.progressbar import ProgressBar
from kivy.uix.boxlayout import BoxLayout
from kivy.core.window import Window
from kivy.uix.behaviors import ButtonBehavior
from kivy.graphics import Color
from kivy.lang import Builder
from logmanager import LogManager
from kivy.properties import StringProperty
import os
 
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.splitter import Splitter

from deviceDescriptor import DeviceDescriptor
from ui_strings import *
from guiConstants import *


OSX_FONT="/Library/Fonts/Arial Unicode.ttf"
UBUNTU_FONT="/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf"
if os.path.isfile( OSX_FONT ):
	FONT_NAME = OSX_FONT
else:
	FONT_NAME = UBUNTU_FONT
	

log = LogManager.get_global_log()

#Constants to change appearance
HUBS_IN_COLUMNS = True # if True, there will be one visual column per hub as defined by the UDEV entry: chip-id-hub-mode
SHOW_STATE = True # if True, shows an Idle.., Testing,  Pass/Fail column. With a 49 port hub, you probably want this to be false

SUCCESS_COLOR = [ 0, 1, 0, 1] # GREEN
FAIL_COLOR = [ 1, 0, 0, 1] # RED
ACTIVE_COLOR = [ 1, 1, 1, 1] # we will use WHITE for active
PASSIVE_COLOR = [ 1, 1, 0, 1] # we will use YELLOW for passive
PROMPT_COLOR = [ 1, .4, .3, 1] # we will use ORANGE for prompts
DISCONNECTED_COLOR = [.3, .3, .3, 1] #when device is disconnected
WHITE_COLOR = [ 1, 1, 1, 1] 
YELLOW_COLOR = [ 1, 1, 0, 1]
PAUSED_COLOR = [ 1, .5, 0, 1]
class TestSuiteGUIView( BoxLayout ):

	def __init__( self, **kwargs ):
		'''
		The view part of the MVC. note that some values are passed in the kwargs dict. See below
		Basically, this method will create and layout the gui's widgets
		'''
		super(TestSuiteGUIView, self).__init__(**kwargs)
		self.deviceDescriptors = kwargs['deviceDescriptors']
		self.deviceUIInfo = kwargs['deviceUIInfo']
		self.hubs = kwargs['hubs']

		#LAYOUT
		outputView = BoxLayout(orientation='vertical') #the right half of the splitter
		self.outputTitle = Label(text=" ", font_size=20, color=YELLOW_COLOR,  size_hint=(1, .1))
		outputView.add_widget(self.outputTitle) #add in a title
			
		self.output = ScrollableLabel()				
		outputView.add_widget(self.output)
		
		splitter = 	Splitter(sizable_from = 'left', min_size = 10, max_size = 600, keep_within_parent = True, size_hint=(.05, 1))
		
		#size the columns appropriately
		rowSizeFactor = 4.0 # 14.0 / rows #adjust font size according to number of rows
		if not SHOW_STATE:
			rowSizeFactor += 1.5
		if HUBS_IN_COLUMNS:
			hubColumns = len(self.hubs)
		else:
			hubColumns = 1

		if HUBS_IN_COLUMNS:
			rowSizeFactor  = rowSizeFactor / hubColumns

		mainButtonWidth = 50 * rowSizeFactor
		hubPanels= GridLayout(cols=hubColumns)

		# Layout the grid for the hubs
		cols = 3
		if not SHOW_STATE:
			cols = cols-1
		for i,hub in enumerate(self.hubs): #go through the hubs
			testingView = GridLayout(cols=cols ,size_hint=(.95, 1)) #the spliter is way off to the right
			hubPanels.add_widget(testingView)
			addTo = testingView #add these to the py grid view. If we want to have many columns, this would add to a sub grid
			for key, deviceDescriptor in self.deviceDescriptors.iteritems(): #now go through devices
				if deviceDescriptor.hub != hub:
					continue #not on this hub, ignore
				
				self._addDeviceWidget(addTo, key,'button',
							Button(text=deviceDescriptor.uid, color = DISCONNECTED_COLOR, font_size=30 * rowSizeFactor, font_name=FONT_NAME, halign="center", size_hint_x=None, width=mainButtonWidth))

				if SHOW_STATE: # global option whether to display the state 
					stateAddTo = addTo
				else:
					stateAddTo = None # the widget is created as an orphan. It needs to exists because other code will try to update it
				self._addDeviceWidget(stateAddTo, key,'stateLabel',
								Label( text = WAITING_TEXT, color = DISCONNECTED_COLOR, font_size=13 * rowSizeFactor, font_name=FONT_NAME, halign="center", size_hint_x=None, width=60 * rowSizeFactor ))
				
				#The label column consists of both text and a progress bar positioned inside a box layout
				stateBox = BoxLayout(orientation='vertical')
				self._addDeviceWidget(stateBox, key,'label',
							LabelButton( text = '', color = DISCONNECTED_COLOR, font_size=13 * rowSizeFactor, font_name=FONT_NAME, halign="center" ))
			
				self._addDeviceWidget(stateBox, key,'progress',
							ProgressBar(value=0, max=1, halign="center",size_hint=(.9, 1.0/15) ))
				
				addTo.add_widget(stateBox)
# 				self._addDeviceWidget(None,key,'output',
# 							LabelButton( text = '', color = WHITE_COLOR, font_size = 10, font_name=FONT_NAME, halign="left" ))
				

		splitter.add_widget(outputView)	
		self.add_widget(hubPanels)
		self.add_widget(splitter)
		
	
	def setOutputDetailTitle(self,title, color = None):
		'''
		Call to set the title of the output window
		:param title: Title of the 
		'''
		self.outputTitle.text=title
		if color:
			self.outputTitle.color = color
		
######################################################################################################################################
# Privates
######################################################################################################################################
	def _addDeviceWidget(self,addTo, key,name,widget):
		widget.id = key
		self.deviceUIInfo[key].widgetInfo[name] = widget
		if addTo:
			addTo.add_widget(widget)
		return widget
		

class LabelButton(ButtonBehavior, Label):
	'''
	This is a mixin which will add the ability to receive push events from a label. No code needed
	'''
	pass

Builder.load_string('''
<ScrollableLabel>:
    Label:
        size_hint_y: None
        height: self.texture_size[1]
        text_size: self.width, None
        text: root.text
''')

class ScrollableLabel(ScrollView):
	text = StringProperty('')

class DeviceUIInfo:
	'''
	Helper class to keep track of the correspondance between a device and the GUI
	'''
	def __init__(self, uid):
		self.uid = uid
		self.state = PASSIVE_STATE
		self.output = " "
		self.widgetInfo = {}
		
	def isActive(self):
		return self.state == ACTIVE_STATE
	
	def isIdle(self):
		return self.state in [PASSIVE_STATE, PAUSED_STATE, PROMPT_STATE, IDLE_STATE]
	
	def isDone(self):
		return self.state in [PASS_STATE, FAIL_STATE]
		

    
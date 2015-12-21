# -*- coding: utf-8 -*-
from kivy.config import Config
# Config.set('graphics', 'fullscreen', '1')
Config.set('graphics', 'width', '1024')
Config.set('graphics', 'height', '768')
Config.set('graphics', 'window_state',"maximized")
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
from kivy.app import App
from kivy.clock import Clock

import os
 
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.splitter import Splitter

from deviceDescriptor import DeviceDescriptor
from runState import RunState
from ui_strings import *
from controller import Controller

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

class KivyApp(App):
	def __init__( self, testSuiteName ):
		super( KivyApp, self ).__init__()
		self.controller = Controller(log,testSuiteName)
		self.kivyUpdateTrigger = Clock.create_trigger(self._onUpdateTrigger.__get__(self,KivyApp)) #kivy Trigger that will be set when added to queue
		self.controller.addUpdateQueueListener(self.kivyUpdateTrigger) #this will be called everytime an update is added to the queue
							
	def build( self ):
		self.controller.configure()
		Clock.schedule_interval(self._onPollingTick.__get__(self, KivyApp),1) # Poll for device changes every second
		self.view = ChipFlashChipView(deviceDescriptors=self.controller.deviceDescriptors, hubs = self.controller.hubs)
		self.view.addMainButtonListener(self._onMainButton.__get__(self,KivyApp)) #observe button events if GUI
		self.controller.addStateListener(self.view.onUpdateStateInfo.__get__(self.view,ChipFlashChipView))
		self.title = self.controller.getTitle()
		return self.view

	def on_stop( self ):
		'''
		Called from Kivy at end of run
		'''
# 		PersistentData.write()
# 		LogManager.close_all_logs()
		pass

	def _onUpdateTrigger(self,x):
		self.controller.onUpdateTrigger(x)
 
 	def _onPollingTick(self,dt):
 		self.controller.onPollingTick(dt)

 	def _onMainButton(self, button):
		'''
		Handle button clicks on id column as triggers to do something
		:param button:
		'''
		self.controller.onMainButton(button)
		
class ChipFlashChipView( BoxLayout ):

	def __init__( self, **kwargs ):
		'''
		The view part of the MVC. note that some values are passed in the kwargs dict. See below
		Basically, this method will create and layout the gui's widgets
		'''
		super(ChipFlashChipView, self).__init__(**kwargs)
		self.deviceDescriptors = kwargs['deviceDescriptors']
		self.hubs = kwargs['hubs']
		self.widgetsMap = {}
		self.outputDetailUid = None #the uid of of what's being shown in the output (detail) view to the right of the splitter
		self.mainButtonListeners = []
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
				
				widgets = Widgets()
				self.widgetsMap[key] = widgets
				
				# The main button
				widgets.button = Button(id = key, text=deviceDescriptor.uid, color = DISCONNECTED_COLOR, font_size=30 * rowSizeFactor, 
																 font_name=FONT_NAME, halign="center", size_hint_x=None, width=mainButtonWidth)
				widgets.button.bind( on_press=self._onClickedMainButton.__get__(self, ChipFlashChipView))
				addTo.add_widget(widgets.button)

				# The state column
				widgets.stateLabel = Label(id = key, text = WAITING_TEXT, color = DISCONNECTED_COLOR, font_size=13 * rowSizeFactor, font_name=FONT_NAME, halign="center", size_hint_x=None, width=60 * rowSizeFactor )
				if SHOW_STATE:
					addTo.add_widget(widgets.stateLabel)
				
				#The label column kists of both text and a progress bar positioned inside a box layout
				stateBox = BoxLayout(orientation='vertical')
				widgets.label = LabelButton(id = key, text = '', color = DISCONNECTED_COLOR, font_size=13 * rowSizeFactor, font_name=FONT_NAME, halign="center" )
				widgets.label.bind( on_press=self._onShowOutput.__get__(self, ChipFlashChipView)) # show output window if label clicked
				stateBox.add_widget(widgets.label)
				widgets.progress = ProgressBar(id = key, value=0, max=1, halign="center",size_hint=(.9, 1.0/15) )
				stateBox.add_widget(widgets.progress)
				addTo.add_widget(stateBox)
				

		splitter.add_widget(outputView)	
		self.add_widget(hubPanels)
		self.add_widget(splitter)
		
	def addMainButtonListener(self, listener):
		'''
		Add an observer to the main button. The Main app will listen to button clicks
		:param listener:
		'''
		self.mainButtonListeners.append(listener)
		
			
	#static
	_stateToColor ={RunState.PASSIVE_STATE: PASSIVE_COLOR, RunState.PASS_STATE: SUCCESS_COLOR, RunState.FAIL_STATE:FAIL_COLOR, RunState.PROMPT_STATE: PROMPT_COLOR, RunState.ACTIVE_STATE:ACTIVE_COLOR, RunState.PAUSED_STATE:PAUSED_COLOR, RunState.IDLE_STATE: PASSIVE_COLOR, RunState.DISCONNECTED_STATE: DISCONNECTED_COLOR}
	
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
		
		widgets = self.widgetsMap[uid]
		if state:
			color = self._stateToColor[state]
			widgets.setColor(color)
			
		if stateLabel:
			widgets.stateLabel.text = stateLabel
										
		if label:
			widgets.label.text = label
			
		if progress:
			widgets.progress.value = progress
		

		if prompt:
			widgets.label.text = prompt
			
		if output:
			widgets.output = output
			self._onShowOutput(None,uid) #if the output detail is showing this output, it will be updated

			
######################################################################################################################################
# Privates
######################################################################################################################################
	def _onClickedMainButton(self, button):
		'''
		When the button is clicked, notify all listeners
		:param button:
		'''
		for listener in self.mainButtonListeners:
			listener(button)
	

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
		widgets = self.widgetsMap[uid]
		title = "Port: " + str(uid)
		color = widgets.label.color # use same color as state
		self._setOutputDetailTitle(title, color)
		self.output.text=widgets.output

	def _setOutputDetailTitle(self,title, color = None):
		'''
		Call to set the title of the output window
		:param title: Title of the 
		'''
		self.outputTitle.text=title
		if color:
			self.outputTitle.color = color
		
class Widgets:
	'''
	Helper class to handle the row widgets
	'''
	def __init__(self):
		self.button = None
		self.stateLabel = None
		self.label= None
		self.progress = None
		self.output = "" #This is actually the output text for the widget
		
	def setColor(self,color):
		'''
		Set all widgets in the row to the same color
		:param color:
		'''
		self.color = color
		self.button.color = color
		self.stateLabel.color = color
		self.label.color = color
		self.progress.color = color


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

########################################################################################
if __name__ == '__main__':
	app = KivyApp("Flasher")
	try:
		app.run()
	except (KeyboardInterrupt, SystemExit):
		app.stop()
    
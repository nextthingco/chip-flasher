# -*- coding: utf-8 -*-
import threading
import time
from flasher.fsm import FSM
# import flasher.station_b
import flasher.station_c
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.progressbar import ProgressBar
from kivy.uix.listview import ListView
from kivy.uix.label import Label
from kivy.core.text import LabelBase
from flasher import states
import os.path
import logging
import sys
log = logging.getLogger('flasher')

OSX_FONT="/Library/Fonts/Arial Unicode.ttf"
UBUNTU_FONT="/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf"
if os.path.isfile( OSX_FONT ):
	FONT_NAME = OSX_FONT
else:
	FONT_NAME = UBUNTU_FONT

def button_callback( instance ):
	if not states.get( instance.name ) is None:
		if not states.get( instance.name ).state is None:
			states.get( instance.name ).trigger = True

class Instance(object):
	def __init__(self, name):
		self.name = name
		self.state = None
		self.thread = None
		self.trigger = False
		self.button = None
		self.progressbar = None
		self.fsm_labels={}
		self.errcode = None

		self.widget = GridLayout( cols=2 )
		innergrid = GridLayout( cols=1 )
		listview = GridLayout( cols=1, size_hint=(0.25, 1) ) #ListView( size_hint=(1, 2), item_strings=[ str(key) for key,value in fsm.iteritems() ])

		fsm = FSM.get_fsm( )
		for key in fsm:
			self.fsm_labels[ key ] = Label( text=fsm[ key ][ "name" ], font_name=FONT_NAME, halign="center" )
			listview.add_widget( self.fsm_labels[ key ] )

		self.widget.add_widget( listview )
		self.widget.add_widget( innergrid )

		self.button = Button(text=name, font_size=76, font_name=FONT_NAME, halign="center")
		self.button.name = name
		self.button.bind( on_press=button_callback )
		innergrid.add_widget( self.button )

		self.progressbar = ProgressBar(value=0, max=100, size_hint=(1, 1.0/15) )
		innergrid.add_widget( self.progressbar )

		self.run()

	def set_progress(self, value, max=100 ):
		self.progressbar.value = value*100.0
		self.progressbar.max = max*100.0

	def get_progress( self ):
		return { "value": self.progressbar.value / 100.0, "max": self.progressbar.max / 100.0 }

	def get_widget(self):
		return self.widget

	def _thread(self):
		log.info( "Thread started" )
		while True:
			if self.is_running is False:
				break

			time.sleep( 0.5 )
			if self.state is None:
				log.error( "No state" )
				continue

			fsm = FSM.get_fsm( )

			if self.errcode is None:
				errvalue = ""
			else:
				errvalue = "\n\n" + str( self.errcode )

			self.fsm_labels[ self.state ].color = ( 0, 1, 0, 1 )
			self.button.text = fsm[ self.state ][ "name" ] + errvalue
			self.button.background_color = fsm[ self.state ][ "color" ]

			if self.trigger is False:
				continue
			else:
				log.info( "Trigger is enabled" )

			# thread callback
			log.debug("State: " + self.state)
			retvalues = fsm[ self.state ][ "callback" ]( self )
			self.errcode = None
			if type(retvalues) is str:
				next_state = retvalues
			elif type(retvalues) is tuple:
				next_state = retvalues[0]
				self.errcode = retvalues[1]
			if not next_state is None:
				log.info( "Transitioning from " + self.state + " to " + next_state )
				self.fsm_labels[ self.state ].color = ( 0, 0, 1, 1 )
				self.trigger = fsm[ next_state ][ "trigger-automatically" ]
				self.state = next_state

	def reset_labels( self ):
		fsm = FSM.get_fsm( )
		for key in fsm:
			self.fsm_labels[ key ].color = ( 1, 1, 1, 1 )

	def stop( self ):
		log.info("Stopping...")
		self.is_running = False

	def run( self ):
		if self.thread is None:
			self.is_running = True
			self.thread = threading.Thread( target=self._thread )
			self.thread.start()

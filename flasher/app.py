# -*- coding: utf-8 -*-
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
import subprocess
from os import path
import logging
log = logging.getLogger('flasher')


def add_new_instance( name, state ):
	if states.get( name ) is None:
		new_instance = Instance( name )
		new_instance.state = state
		states.set( name, new_instance )
		return new_instance


class FlasherScreen(GridLayout):
	def add_instance(self, name):
		self.instances[ name ] = add_new_instance( name, "idle" )
		self.instances[ name ].name = name
		self.add_widget( self.instances[ name ].get_widget() )

	def __init__(self, **kwargs):
		super(FlasherScreen, self).__init__(**kwargs)
		self.keyboard = Window.request_keyboard(self.keyboard_closed, self)
		self.keyboard.bind( on_key_down=self.on_keyboard_down )
		self.keyboard.bind( on_key_up=self.on_keyboard_up )
		self.cols = 5
		self.instances = {}
		self.add_instance("CHIP 1")

	def keyboard_closed(self):
		self.keyboard.unbind( on_key_down=self._on_keyboard_down )
		self.keyboard.unbind( on_key_up=self.on_keyboard_up )
		self.keyboard = None

	def on_keyboard_down(self, keyboard, keycode, text, modifiers):
		root = BoxLayout()
		if keycode[1] == '1':
			self.children[0].background_color=[1,0,0,1]
		return True

	def on_keyboard_up(self, keyboard, keycode):
		root = BoxLayout()
		if keycode[1] == '1':
			self.children[0].background_color=[0,1,0,1]
		return True

class FlasherApp(App):
	def update_title( self, dt ):
		cwd = path.dirname( path.dirname( path.realpath( __file__ ) ) )
		rev = subprocess.Popen( ["git", "rev-parse","HEAD"],cwd=cwd, stdout=subprocess.PIPE ).communicate()[0]
		if rev != self.rev:
			log.info( "Flasher Revision: " + rev[0:10] )
		try:
			with open(cwd+"/tools/.firmware/images/build") as myfile:
				build = myfile.read().strip("\n")
		except:
			build = ""

		if build != self.build:
			log.info( "Firmware Build: " + build )
		self.build = build
		self.rev = rev
		self.title = "Flasher Revision: " + self.rev[0:10] + " | Firmware Build: " + self.build

	def build( self ):
		self.rev = 0
		self.build = ""
		cwd = path.dirname( path.dirname( path.realpath( __file__ ) ) )
		
		handler = logging.FileHandler( cwd+"/flasher.log" )
		formatter = logging.Formatter( '%(asctime)s %(levelname)s %(message)s' )
		handler.setFormatter( formatter )
		log.addHandler( handler )
		log.setLevel( logging.INFO )

		Clock.schedule_interval( self.update_title, 0.5 )
		return FlasherScreen()

	def on_stop( self ):
		states.stop()

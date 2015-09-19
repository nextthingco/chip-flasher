import threading
import time
from flasher.fsm import fsm
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.progressbar import ProgressBar
from kivy.uix.listview import ListView
from kivy.uix.label import Label
from flasher import states
import logging
log = logging.getLogger('flasher')

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

		self.widget = GridLayout(cols=2)

		innergrid = GridLayout(cols=1)

		listview = ListView( size_hint=(1, 2), item_strings=[str(key) for key,value in fsm.iteritems()])

		#for key, value in fsm.iteritems():
		#	listview.add_widget( Label( text=key ) )

		self.widget.add_widget( listview )
		self.widget.add_widget( innergrid )


		self.button = Button(text=name, font_size=76)
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
		log.info("Thread started")
		while True:
			if self.is_running is False:
				break
			time.sleep( 0.5 )
			if self.state is None:
				log.error("No state")
				continue

			self.button.text = fsm[ self.state ][ "name" ]
			self.button.background_color = fsm[ self.state ][ "color" ]

			if self.trigger is False:
				continue
			else:
				log.info("Trigger is enabled")

			# thread callback
			next_state = fsm[ self.state ][ "callback" ]( self )
			if not next_state is None:
				log.info( "Transitioning from " + self.state + " to " + next_state )
				self.trigger = fsm[ next_state ][ "trigger-automatically" ]
				self.state = next_state

	def stop(self):
		log.info("Stopping...")
		self.is_running = False

	def run(self):
		if self.thread is None:
			self.is_running = True
			self.thread = threading.Thread( target=self._thread )
			self.thread.start()

import threading
import time
from flasher.fsm import fsm
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.progressbar import ProgressBar
from flasher import states
import logging
log = logging.getLogger('flasher')

def button_callback( instance ):
	if not states.get(instance.name) is None:
		if not states.get(instance.name).state is None:
			states.get(instance.name).trigger = True

class Instance(object):
	def __init__(self, name):
		self.name = name
		self.state = None
		self.thread = None
		self.trigger = False

		self.widget = GridLayout(cols=1)

		button = Button(text=name, font_size=76)
		button.name = name
		button.bind( on_press=button_callback )
		self.widget.add_widget( button )

		pb = ProgressBar(value=25, max=100)
		self.widget.add_widget( pb )

		self.run()

	def get_widget(self):
		return self.widget

	def _thread(self):
		print("Thread started")
		while True:
			if self.is_running is False:
				break
			time.sleep( 0.5 )
			if self.state is None:
				print("No state")
				continue

			self.widget.children[1].text = fsm[ self.state ][ "name" ]
			self.widget.children[1].background_color = fsm[ self.state ][ "color" ]

			if self.trigger is False:
				continue
			else:
				print("Trigger is enabled")

			# thread callback
			next_state = fsm[ self.state ][ "callback" ]( self.widget )
			if not next_state is None:
				log.info( "Transitioning from " + self.state + " to " + next_state )
				print( "Transitioning from " + self.state + " to " + next_state )
				self.trigger = fsm[ next_state ][ "trigger-automatically" ]
				self.state = next_state

	def stop(self):
		print("Stopping...")
		self.is_running = False
		#if self.thread.is_alive():
		#	self.thread.join()

	def run(self):
		if self.thread is None:
			self.is_running = True
			self.thread = threading.Thread( target=self._thread )
			self.thread.start()

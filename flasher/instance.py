import threading
import time
from flasher.fsm import fsm

class Instance(object):
	def __init__(self, instance):
		self.instance = instance
		self.state = None
		self.thread = None
		self.trigger = False
		self.run()

	def _thread(self):
		print("Thread started")
		while True:
			if self.is_running is False:
				break
			time.sleep( 0.5 )
			if self.state is None:
				print("No state")
				continue

			self.instance.text = fsm[ self.state ][ "name" ]
			self.instance.background_color = fsm[ self.state ][ "color" ]

			if self.trigger is False:
				continue
			else:
				print("Trigger is enabled")

			# thread callback
			next_state = fsm[ self.state ][ "callback" ]( self.instance )
			if not next_state is None:
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

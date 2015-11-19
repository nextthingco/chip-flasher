import threading
import time
import socket #for getting hostname
from flasher.fsm import fsm
import logging
log = logging.getLogger('flasher')
UBUNTU = 0
CHIP = 1
class Instance(object):
	def __init__(self, instance):
		self.instance = instance
		self.state = None
		self.thread = None
		self.trigger = False
		hostname = socket.gethostname()
		# Figure out what machine is doing the flashing. This will determine which timeout values to use
		self.flashingDevice = CHIP if hostname == 'chip' else UBUNTU
		self.timeout = 0 #States can specify a timeout which gets used by the callbacks
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
			if "timeout" in fsm[self.state]:
				self.instance.timeout = fsm[self.state]["timeout"][self.flashingDevice]
			else:
				self.instance.timeout = 0
			if self.trigger is False:
				continue
			else:
				print("Trigger is enabled")

			# thread callback
			next_state = fsm[ self.state ][ "callback" ]( self.instance )
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

		

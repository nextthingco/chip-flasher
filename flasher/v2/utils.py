# -*- coding: utf-8 -*-
import time
import subprocess
import os
import signal
from os import path
from kivy.clock import Clock
from functools import partial
from threading import Timer
import cmd
# from observed import observable_method

class Progress(object):
	def __init__(self, start = 0.0, finish=100.0):
		self.start = start
		self.finish = finish
		self.current = start
	
	def addProgress(self,change):
		self.setProgress(self.current + change)

# 	@observable_method	
	def setProgress(self, value):
		self.current = value
		
	def getProgress(self):
		return self.current / self.finish
	
class CommandRunner:
	def __init__(self,log):
		self.log = log
		self.progress=Progress()

	# calls a shell command
	def call_and_return(self, cmd, timeout=1, expectedTime=60):
		self.expectedTime = expectedTime
		self.progress.finish =expectedTime
		
		log = self.log
		log.info('ENTER: call_and_return()')
		working_dir=path.dirname( path.dirname( path.realpath( __file__ ) ) )
		my_env = os.environ.copy()
		my_env["BUILDROOT_OUTPUT_DIR"] = working_dir+"/tools/.firmware/"
		proc = subprocess.Popen( cmd, cwd=working_dir+"/tools", shell=False, preexec_fn=os.setsid, env=my_env )
		timer = Timer( timeout, os.killpg, [ proc.pid, signal.SIGTERM ] )
		returncode = None
		try:
			timer.start()
			Clock.schedule_interval(self.progress.addProgress.__get__(self.progress, Progress), 1.0/expectedTime ) # callback for bound method
			proc.communicate()
			proc.wait()
			returncode = proc.returncode
		finally:
			timer.cancel()
			Clock.unschedule(self.progress.addProgress)
# 			instance.set_progress( 1, 1 )
			log.info('error code='+str(proc.returncode))
			log.info('LEAVE: call_and_return()')
			if proc.returncode < 0:
				log.info('Timeout occurred!')
			
			if proc.poll():
				log.error("Process " + str(proc.pid) + " is still running!")
			return returncode

# -*- coding: utf-8 -*-
import subprocess
import os
import signal
from os import path
from kivy.clock import Clock
from threading import Timer
from progress import Progress
	
class CommandRunner:
	'''
	This class executes a shell command and returns a return code
	It also will update any progress observers
	'''
	def __init__(self,log, progressObservers = None, expectedTime = None):
		'''
		:param log: Logger to use. If running in Kivy, it will use a Kivy logger
		:param progressObservers: Any observers to be notitifed of progress
		:param expectedTime: How long the subprocess should take. Used for updating progress 
		'''
		self.log = log
		self.progress=Progress(progressObservers)
		self.expectedTime = expectedTime

	def call_and_return(self, cmd, timeout=1, expectedTime=60):
		'''
		Spawn a subprocess and return the return code
		This maybe could be simplified by using pexpect.run()
		:param cmd: Command to run. Can be array
		:param timeout: timeout of the process. Is this working?
		:param expectedTime: How long we think it should take
		'''
		self.expectedTime = expectedTime
		self.progress.finish =expectedTime
		
		log = self.log
		log.info('ENTER: call_and_return()')
		working_dir=path.dirname( path.dirname( path.realpath( __file__ ) ) )
		my_env = os.environ.copy()
		my_env["BUILDROOT_OUTPUT_DIR"] = working_dir+"/flasher/tools/.firmware/"
		print working_dir + "/flasher/tools"
		

		proc = subprocess.Popen( cmd, cwd=working_dir+"/flasher/tools", shell=False, preexec_fn=os.setsid, env=my_env, stdout=subprocess.PIPE )

		print "++++++++++++++++++++++ timeout is  " + str(timeout) + "  ++++++++++++++++++++++++++++++++"		
		timer = Timer( timeout, os.killpg, [ proc.pid, signal.SIGTERM ] ) #timeout will signal process to kill
		returncode = None
				
		try:
			timer.start()
			Clock.schedule_interval(self.progress.addProgress.__get__(self.progress, Progress), 1.0/expectedTime ) # callback for bound method
			out ,err = proc.communicate()
			#currently, the output is only updated at the end of the process. An alternative would be to
			# do like here: http://stackoverflow.com/questions/2804543/read-subprocess-stdout-line-by-line
			# There should be an observer passed in (like progress observer) which should be notified after
			# every line and update the GUI
			proc.wait()
			returncode = proc.returncode
		finally:
			timer.cancel()
			Clock.unschedule(self.progress.addProgress)
			log.info('error code='+str(proc.returncode))
			log.info('LEAVE: call_and_return()')
			if proc.returncode < 0:
				log.info('Timeout occurred!')
			
			if proc.poll():
				log.error("Process " + str(proc.pid) + " is still running!")
			return out, returncode

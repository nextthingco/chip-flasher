# -*- coding: utf-8 -*-
import time
import subprocess
import os
import signal
from os import path
from kivy.clock import Clock
from functools import partial
from threading import Timer

# calls a shell command
def call_and_return(instance, cmd, serialLog, timeout=1):
	def update_progress_bar( dt ):
		progress = instance.get_progress()
		progress["value"] = progress["value"] + dt
		if progress["value"] >= progress["max"]:
			progress["value"] = progress["max"]

		instance.set_progress( progress["value"], progress["max"] )


	serialLog.info('ENTER: call_and_return()')
	working_dir=path.dirname( path.dirname( path.realpath( __file__ ) ) )
	my_env = os.environ.copy()
	my_env["BUILDROOT_OUTPUT_DIR"] = working_dir+"/tools/.firmware/"
	proc = subprocess.Popen( cmd, cwd=working_dir+"/tools", shell=False, preexec_fn=os.setsid, env=my_env )
	timer = Timer( timeout, os.killpg, [ proc.pid, signal.SIGTERM ] )
	returncode = None
	time_elapsed = 0
	try:
		timer.start()
		instance.set_progress( 0, timeout )
		Clock.schedule_interval( update_progress_bar, 1.0/60.0 )
		proc.communicate()
		proc.wait()
		returncode = proc.returncode
	finally:
		timer.cancel()
		Clock.unschedule( update_progress_bar )
		instance.set_progress( 1, 1 )
		serialLog.info('error code='+str(proc.returncode))
		serialLog.info('LEAVE: call_and_return()')
		if proc.returncode < 0:
			serialLog.info('Timeout occurred!')
		
		if proc.poll():
			serialLog.error("Process " + str(proc.pid) + " is still running!")
		return returncode

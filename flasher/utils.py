import time
import subprocess
import os
import signal
from os import path
from threading import Timer
import logging
log = logging.getLogger('flasher')

# calls a shell command
def call_and_return(timeout=1, *args, **kwargs):
	log.info('ENTER: call_and_return()')
	working_dir=path.dirname(path.dirname(path.realpath(__file__)))
	proc = subprocess.Popen(args, cwd=working_dir+"/tools", shell=False, preexec_fn=os.setsid)
	timer = Timer( timeout, os.killpg, [proc.pid, signal.SIGTERM] )
	returncode = None
	try:
		timer.start()
		proc.communicate()
		proc.wait()
		returncode = proc.returncode
		log.info('error code='+str(proc.returncode))
		log.info('LEAVE: call_and_return()')
	finally:
		timer.cancel()
		log.info('error code='+str(proc.returncode))
		log.info('LEAVE: call_and_return()')
		if proc.returncode < 0:
			log.info('Timeout occurred!')
		
		if proc.poll():
			log.error("Process " + str(proc.pid) + " is still running!")
		return returncode

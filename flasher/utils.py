import time
import subprocess
from os import path
import logging
log = logging.getLogger('flasher')

# calls a shell command
def call_and_return( *args, **kwargs ):
  print('ENTER: call_and_return()')
  working_dir=path.dirname(path.dirname(path.realpath(__file__)))
  time.sleep( 1 )
  proc = subprocess.Popen(args, cwd=working_dir+"/tools" )
  proc.communicate()
  print('error code='+str(proc.returncode))
  print('LEAVE: call_and_return()')
  return proc.returncode

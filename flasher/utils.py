import time
import subprocess
from os import path

# calls a shell command
def call_and_return( *args, **kwargs ):
	working_dir=path.dirname(path.dirname(path.realpath(__file__)))
	print("Working dir %s" % working_dir)
	time.sleep( 1 )
	proc = subprocess.Popen(args, cwd=working_dir+"/tools" )
	proc.communicate()
	return proc.returncode

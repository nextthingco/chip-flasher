import logging
import os
import calendar
import time
from os import path

cwd = path.dirname( path.dirname( path.realpath( __file__ ) ) )
class LogManager( object ):
	logfiles = {}
	formatter = logging.Formatter( "%(asctime)s %(levelname)s %(message)s" )

	@staticmethod
	def setup():
		logspath = cwd + "/logs"
		if not path.exists( logspath ):
			try:
				os.makedirs( logspath )
			except OSError as exc:
				if exc.errno == errno.EEXIST and os.path.isdir( logspath ):
					pass
				else: raise

	@staticmethod
	def get_global_log():
		LogManager.setup()
		if not "global" in LogManager.logfiles:
			logfilename = "/flasher.log"
			logfilepath = cwd + "/logs/" + logfilename
			handler = logging.FileHandler( logfilepath )
			handler.setFormatter( LogManager.formatter )

			log = logging.getLogger("global")
			log.addHandler( handler )
			log.setLevel( logging.INFO )
			LogManager.logfiles[ "global" ] = {
				"handler" : handler,
				"log" : log,
				"filename" : logfilename
			}
			

		return LogManager.logfiles[ "global" ][ "log" ]

	@staticmethod
	def get_instanced_log( id ):
		LogManager.setup()
		if not id in LogManager.logfiles:
			curtime = calendar.timegm(time.gmtime())

			logfilename = "flasher-{1}-{0}.log".format( curtime, id )
			logfilepath = cwd + "/logs/" + logfilename
			handler = logging.FileHandler( logfilepath )
			handler.setFormatter( LogManager.formatter )

			log = logging.getLogger( str(id) )
			log.addHandler( handler )
			log.setLevel( logging.INFO )
			LogManager.logfiles[ str(id) ] = {
				"handler" : handler,
				"log" : log,
				"filename" : logfilename
			}
			return LogManager.logfiles[ str(id) ]["log"]

	@staticmethod
	def close_instanced_log( id ):
		if id in LogManager.logfiles:
			LogManager.logfiles[ str(id) ]["handler"].close()
			del LogManager.logfiles[ str(id) ]

	@staticmethod
	def close_all_logs():
			for k,v in LogManager.logfiles.items():
				LogManager.close_instanced_log( k )
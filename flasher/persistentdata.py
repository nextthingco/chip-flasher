import json
from os import path
from logmanager import LogManager

cwd = path.dirname( path.dirname( path.realpath( __file__ ) ) )
log = LogManager.get_global_log()

class PersistentData( object ):
	data = {}
	stats_filename = cwd + "/.stats.json"

	@staticmethod
	def read():
		try:
			with open( PersistentData.stats_filename ) as myfile:
				string = myfile.read().strip( "\n" )
				PersistentData.data = json.loads( string )

				if not PersistentData.data:
					PersistentData.data = {}

				log.info( "Successfully read from " + PersistentData.stats_filename )
		except:
			log.error( "Failed to read from " + PersistentData.stats_filename )
			PersistentData.data = {}

		if not PersistentData.exists( "py-count" ):
			print( "Can't find py-count" )
			PersistentData.set( "py-count", 0 )

	@staticmethod
	def write():
		try:
			with open( PersistentData.stats_filename,'w' ) as myfile:
				myfile.write( json.dumps( PersistentData.data, indent=4, sort_keys=True ) )
		except:
			log.error( "Failed to write to " + PersistentData.stats_filename )

	@staticmethod
	def get( key ):
		if key in PersistentData.data:
			return PersistentData.data[ key ]
		else:
			return None

	@staticmethod
	def exists( key ):
		if key in PersistentData.data:
			return True
		else:
			return False

	@staticmethod
	def set( key, value ):
		PersistentData.data[ key ] = value
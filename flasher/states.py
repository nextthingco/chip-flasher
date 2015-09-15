states = {}
def get(key):
	if key in states:
		return states[ key ]
	else:
		return None

def set(key, value):
		states[ key ] = value

def stop():
	for key, state in states.iteritems():
		state.stop()
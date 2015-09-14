from kivy.config import Config
# Config.set('graphics', 'fullscreen', '1')

from kivy.app import App
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.boxlayout import BoxLayout
from kivy.core.window import Window
import usb1
import subprocess
import threading
import os
import time

# calls a shell command
def call_and_return( *args, **kwargs ):
	working_dir=os.path.dirname(os.path.realpath(__file__))
	print("Working dir %s" % working_dir)
	proc = subprocess.Popen(args, cwd=working_dir+"/tools" )
	proc.communicate()
	return proc.returncode

def wait_for_usb( type ):
	start = time.time()
	usb = USB()
	devices = []
	print( "Length: " + str( len( devices ) ) )
	while len( devices ) == 0:
		if time.time() >= (start + 30):
			return False
		devices = usb.find_device( type )
		time.sleep( 1 )
	return True

# FSM callbacks
def on_idle( instance ):
	transition_state( instance, "wait-for-fel" )

def on_wait_for_fel( instance ):
	if wait_for_usb("fel"):
		transition_state( instance, "upload" )
	else:
		transition_state( instance, "failure" )

def on_upload( instance ):
	if call_and_return("./chip-update-firmware.sh", "-f") != 0:
	# if call_and_return("false") != 0:
		transition_state( instance, "wait-for-serial" )
	else:
		transition_state( instance, "failure" )

####
def on_wait_for_serial( instance ):
	if wait_for_usb("serial-gadget"):
		transition_state( instance, "success" )
	else:
		transition_state( instance, "failure" )
def on_verify( instance ):
	#start = time.time()
	#exit = False
	#while True:
	#	time.sleep(1)
	#	if time.time() >= (start + 30):
	#		#timeout
	#		transition_state( instance, 7 )
	#		return
	#	usb = USB()
	#	devices = usb.find_device("serial-gadget")
	#	print("Length: " + str(len(devices)))
	#	if len(devices) > 0:
	if call_and_return("false") != 0:
		transition_state( instance, "verify" )
	else:
		transition_state( instance, "failure" )
	
		

def on_success( instance ):
	time.sleep(5)
	transition_state( instance, "idle" )

def on_failure( instance ):
	time.sleep(20)
	transition_state( instance, "idle" )

fsm = {
	"idle": {
		"name": "Idle",
		"color": [	0,		0,	0,	1],
		"callback": on_idle
	},
	"wait-for-fel": {
		"name": "Waiting for FEL device",
		"color": [	1,		0,	1,	1],
		"callback": on_wait_for_fel
	},
	"upload": {
		"name": "Uploading",
		"color": [0.75,	 0.25,	0,	1],
		"callback": on_upload
	},
	"wait-for-serial": {
		"name": "Waiting for USB Serial Gadget",
		"color": [	1,		1,	1,	1],
		"callback": on_wait_for_serial
	},
	"verify": {
		"name": "Verifying",
		"color": [	0,		1,	1,	1],
		"callback": on_verify
	},
	"success": {
		"name": "Success",
		"color": [	0,		1,	0,	1],
		"callback": on_success
	},
	"failure": {
		"name": "Failure",
		"color": [	1,		0,	0,	1],
		"callback": on_failure
	},
}

states = {
}

def add_new_instance( instance ):
	if not instance.name in states:
		states[ instance.name ] = {
			"state" : "idle",
			"thread": None
		}

def get_instance_thread( instance ):
	if instance.name in states:
		current_thread = states[ instance.name ][ "thread" ]
		if not current_thread is None and not threading.Thread.is_alive( current_thread ):
			current_thread.join()
			current_thread = None
			states[ instance.name ][ "thread" ] = None
		return current_thread

def launch_instance_thread( instance, args):
	if instance.name in states:
		current_thread = get_instance_thread( instance )
		if current_thread is None:
			current_thread = threading.Thread( target=button_thread, args=args )
			current_thread.start()
			states[ instance.name ][ "thread" ] = current_thread

def transition_state( instance, state, stop=False ):
	if instance.name in states:
		states[ instance.name ][ "state" ] = state
		if not stop:
			launch_instance_thread( instance, [ instance ] )

def update_button_status( instance ):
	if instance.name in states:
		state = fsm[ states[ instance.name ][ "state" ] ]
		instance.text = state[ "name" ]
		instance.background_color = state[ "color" ]

def call_button_callback( instance ):
	if instance.name in states:
		state = states[ instance.name ]
		fsm[ state[ "state" ] ][ "callback" ]( instance )

def button_callback(instance):
	launch_instance_thread( instance, [ instance ] )

def button_thread( args ):
	call_button_callback( args )
	update_button_status( args )

class LoginScreen(GridLayout):

	def add_button(self, name):
		self.buttons[ name ] = Button(text=name)
		self.buttons[ name ].name = name
		self.buttons[ name ].bind( on_press=button_callback )
		self.add_widget( self.buttons[ name ] )
		add_new_instance( self.buttons[ name ] )
		update_button_status( self.buttons[ name ] )


	def __init__(self, **kwargs):
		super(LoginScreen, self).__init__(**kwargs)
		self._keyboard = Window.request_keyboard(self._keyboard_closed, self)
		self._keyboard.bind(on_key_down=self.on_keyboard_down)
		self._keyboard.bind(on_key_up=self.on_keyboard_up)
		self.cols = 5
		self.buttons = {}
		
		self.add_button("CHIP 1")

	def _keyboard_closed(self):
		self._keyboard.unbind(on_key_down=self._on_keyboard_down)
		self._keyboard.unbind(on_key_up=self.on_keyboard_up)
		self._keyboard = None

	def on_keyboard_down(self, keyboard, keycode, text, modifiers):
		root = BoxLayout()
		if keycode[1] == '1':
			self.children[0].background_color=[1,0,0,1]
		return True

	def on_keyboard_up(self, keyboard, keycode):
		root = BoxLayout()
		if keycode[1] == '1':
			self.children[0].background_color=[0,1,0,1]
		return True


class USB(object):
	def __init__(self):
		self.context = usb1.USBContext()
		self.usb_devices = {
			"fel": {
				"vid" : 0x1f3a,
				"pid" : 0xefe8,
			},
			"serial-gadget": {
				"vid" : 0x0525,
				"pid" : 0xa4a7,
			}
		}
	def find_vid_pid(self, vid, pid):
		devices = []
		for device in self.context.getDeviceList(skip_on_access_error=True, skip_on_error=True):
			if device.getVendorID() == vid and device.getProductID() == pid:
				devices.append(device)
		return devices
	def find_device(self, device_name):
		if device_name in self.usb_devices:
			device = self.usb_devices[ device_name ]
			return self.find_vid_pid( device["vid"], device["pid"] )
		return None

class MyApp(App):

	def build(self):
		return LoginScreen()


if __name__ == '__main__':
	MyApp().run()
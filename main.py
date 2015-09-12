from kivy.app import App
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.boxlayout import BoxLayout
from kivy.core.window import Window
import subprocess
import threading
import os

# calls a shell command
def call_and_return( *args, **kwargs ):
	proc = subprocess.Popen(args, cwd=os.getcwd() )
	proc.communicate()
	return proc.returncode

def on_unavailable( instance ):
	if call_and_return("./test.sh") != 0:
		change_button_state( instance, 1 )

def on_ready( instance ):
	change_button_state( instance, 2 )

def on_uploading( instance ):
	if call_and_return("./chip-fel-flash.sh") != 0:
		change_button_state( instance, 6 )
	else:
		change_button_state( instance, 7 )

####
def on_flashing( instance ):
	if call_and_return("./test.sh") != 0:
		change_button_state( instance, 4 )
	else:
		change_button_state( instance, 7 )
def on_booting( instance ):
	if call_and_return("./test.sh") != 0:
		change_button_state( instance, 5 )
	else:
		change_button_state( instance, 7 )
def on_verifying( instance ):
	if call_and_return("./test.sh") != 0:
		change_button_state( instance, 6 )
	else:
		change_button_state( instance, 7 )

def on_success( instance ):
	change_button_state( instance, 0 )

def on_failure( instance ):
	change_button_state( instance, 0 )

states = {
    0: ["Unavailable",	[	0,		0,	0,	1],	on_unavailable],
    1: ["Ready",		[	1,		0,	1,	1],	on_ready],
    2: ["Uploading",	[0.75,	 0.25,	0,	1],	on_uploading],
    3: ["Flashing",		[	1,		1,	1,	1],	on_flashing],
    4: ["Booting",		[	0,		0,	1,	1],	on_booting],
    5: ["Verifying",	[	0,		1,	1,	1],	on_verifying],
    6: ["Success",		[	0,		1,	0,	1],	on_success],
    7: ["Failure",		[	1,		0,	0,	1],	on_failure],
}

instance_states = {
}

def add_new_instance( instance ):
	if not instance.name in instance_states:
		instance_states[ instance.name ] = {
			"state" : 0,
			"thread": None
		}

def get_instance_thread( instance ):
	if instance.name in instance_states:
		current_thread = instance_states[ instance.name ]["thread"]
		if not current_thread is None and not threading.Thread.is_alive( current_thread ):
			current_thread.join()
			current_thread = None
			instance_states[ instance.name ]["thread"] = None
		return current_thread

def launch_instance_thread( instance, args):
	if instance.name in instance_states:
		current_thread = get_instance_thread( instance )
		if current_thread is None:
			current_thread = threading.Thread(target=button_thread, args=args)
			current_thread.start()
			instance_states[ instance.name ]["thread"] = current_thread

def change_button_state( instance, state ):
	if instance.name in instance_states:
		instance_states[ instance.name ]["state"] = state

def update_button_status( instance ):
	if instance.name in instance_states:
		state_number = instance_states[ instance.name ]["state"]
		current_state = states[ state_number ]
		instance.text=current_state[0]
		instance.background_color=current_state[1]

		call_button_callback( instance )

def call_button_callback( instance ):
	if instance.name in instance_states:
		current_state = states[ instance_states[ instance.name ]["state"] ]
		current_state[2]( instance )

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



class MyApp(App):

	def build(self):
		return LoginScreen()


if __name__ == '__main__':
	MyApp().run()
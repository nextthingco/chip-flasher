from kivy.app import App
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.boxlayout import BoxLayout
from kivy.core.window import Window
import subprocess
import os

# calls a shell command
def call_and_return( *args, **kwargs ):
	proc = subprocess.Popen(args, cwd=os.getcwd() )
	proc.communicate()
	return proc.returncode

def on_unavailable( instance ):
	if call_and_return("./test.sh") != 0:
		change_button_state( instance, 1 )
	else:
		change_button_state( instance, 7 )
def on_ready( instance ):
	if call_and_return("./test.sh") != 0:
		change_button_state( instance, 2 )
	else:
		change_button_state( instance, 7 )
	pass
def on_uploading( instance ):
	if call_and_return("./test.sh") != 0:
		change_button_state( instance, 3 )
	else:
		change_button_state( instance, 7 )
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
    3: ["Flashing",		[	0,		0,	0,	1],	on_flashing],
    4: ["Booting",		[	0,		0,	0,	1],	on_booting],
    5: ["Verifying",	[	0,		0,	0,	1],	on_verifying],
    6: ["Success",		[	0,		1,	0,	1],	on_success],
    7: ["Failure",		[	1,		0,	0,	1],	on_failure],
}

button_states = {
	"A1": { "state" : 0 },
	"A2": { "state" : 0 },
	"A3": { "state" : 0 },
	"A4": { "state" : 0 },
	"A5": { "state" : 0 },
	"B1": { "state" : 0 },
	"B2": { "state" : 0 },
	"B3": { "state" : 0 },
	"B4": { "state" : 0 },
	"B5": { "state" : 0 }
}

def change_button_state( instance, state ):
	if instance.name in button_states:
		button_states[ instance.name ]["state"] = state

def update_button_status( instance ):
	if instance.name in button_states:
		state_number = button_states[ instance.name ]["state"]
		current_state = states[ state_number ]
		instance.text=current_state[0]
		instance.background_color=current_state[1]

def call_button_callback( instance ):
	if instance.name in button_states:
		current_state = states[ button_states[ instance.name ]["state"] ]
		current_state[2]( instance )

def button_callback(instance):
	call_button_callback( instance )
	update_button_status( instance )


class LoginScreen(GridLayout):

	def __init__(self, **kwargs):
		super(LoginScreen, self).__init__(**kwargs)
		self._keyboard = Window.request_keyboard(self._keyboard_closed, self)
		self._keyboard.bind(on_key_down=self.on_keyboard_down)
		self._keyboard.bind(on_key_up=self.on_keyboard_up)
		self.cols = 5
		
		# A1
		self.btnA1=Button(text='A1')
		self.btnA1.name="A1"
		self.btnA1.bind(on_press=button_callback)
		self.add_widget(self.btnA1)
		
		# A2
		self.btnA2=Button(text='A2')
		self.btnA2.name="A2"
		self.btnA2.bind(on_press=button_callback)
		self.add_widget(self.btnA2)
		
		# A3
		self.btnA3=Button(text='A3')
		self.btnA3.name="A3"
		self.btnA3.bind(on_press=button_callback)
		self.add_widget(self.btnA3)
		
		# A4
		self.btnA4=Button(text='A4')
		self.btnA4.name="A4"
		self.btnA4.bind(on_press=button_callback)
		self.add_widget(self.btnA4)
		
		# B5
		self.btnA5=Button(text='A5')
		self.btnA5.name="A5"
		self.btnA5.bind(on_press=button_callback)
		self.add_widget(self.btnA5)

		# B1
		self.btnB1=Button(text='B1')
		self.btnB1.name="B1"
		self.btnB1.bind(on_press=button_callback)
		self.add_widget(self.btnB1)
		
		# B2
		self.btnB2=Button(text='B2')
		self.btnB2.name="B2"
		self.btnB2.bind(on_press=button_callback)
		self.add_widget(self.btnB2)
		
		# B3
		self.btnB3=Button(text='B3')
		self.btnB3.name="B3"
		self.btnB3.bind(on_press=button_callback)
		self.add_widget(self.btnB3)
		
		# B4
		self.btnB4=Button(text='B4')
		self.btnB4.name="B4"
		self.btnB4.bind(on_press=button_callback)
		self.add_widget(self.btnB4)
		
		# B5
		self.btnB5=Button(text='B5')
		self.btnB5.name="B5"
		self.btnB5.bind(on_press=button_callback)
		self.add_widget(self.btnB5)

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
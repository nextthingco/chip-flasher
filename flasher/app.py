from kivy.config import Config
# Config.set('graphics', 'fullscreen', '1')

from kivy.app import App
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.boxlayout import BoxLayout
from kivy.core.window import Window
from flasher.instance import Instance
from flasher import states

def button_callback( instance ):
	if not states.get(instance.name) is None:
		if not states.get(instance.name).state is None:
			states.get(instance.name).trigger = True

def add_new_instance( instance, state ):
	if states.get( instance.name ) is None:
		new_instance = Instance( instance )
		new_instance.state = state
		states.set( instance.name, new_instance )


class FlasherScreen(GridLayout):

	def add_button(self, name):
		self.buttons[ name ] = Button(text=name, font_size=76)
		self.buttons[ name ].name = name
		self.buttons[ name ].bind( on_press=button_callback )
		self.add_widget( self.buttons[ name ] )
		add_new_instance( self.buttons[ name ], "idle" )


	def __init__(self, **kwargs):
		super(FlasherScreen, self).__init__(**kwargs)
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

class FlasherApp(App):

	def build(self):
		return FlasherScreen()

	def on_stop(self):
		states.stop()

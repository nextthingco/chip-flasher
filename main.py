from flasher.app import FlasherApp
from flasher.usb import USB



if __name__ == '__main__':
	app = FlasherApp()
	try:
		app.run()
	except (KeyboardInterrupt, SystemExit):
		app.stop()

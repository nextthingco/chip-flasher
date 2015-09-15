import usb1
import time

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
		for device in self.context.getDeviceList( skip_on_access_error=True, skip_on_error=True ):
			if device.getVendorID() == vid and device.getProductID() == pid:
				devices.append(device)
		return devices
	def find_device(self, device_name):
		if device_name in self.usb_devices:
			device = self.usb_devices[ device_name ]
			return self.find_vid_pid( device["vid"], device["pid"] )
		return None


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

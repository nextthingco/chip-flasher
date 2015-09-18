import usb1
import time
import logging
from threading import Timer
log = logging.getLogger('flasher')

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

kill = False
def timer_kill( type ):
  global kill
  kill = True
  log.error("Timed out while waiting for usb device: " + type)

def wait_for_usb( type, timeout=60):
  global kill
  start = time.time()
  usb = USB()
  devices = []
  timer = Timer(timeout, timer_kill, [ type ])
  kill = False
  try:
    timer.start()
    while kill is False:
      time.sleep( 1 )
      devices = usb.find_device( type )
      if len( devices ) > 0:
        return True
  finally:
    timer.cancel()
    return False
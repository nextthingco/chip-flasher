'''
Created on Mar 15, 2017

@author: howie

This module serves to let us access usb devices by their udev symlink
'''
import usb.core
import usb.util
import pyudev

udevContext = pyudev.Context()

def symlinkToBusAddress(symlink):
    '''
    Search udev for the symlink, returning the bus and device numbers. returns None if not found
    '''
    try:
        dev = pyudev.Devices.from_device_file(udevContext, '/dev/' + symlink) #will throw if not found
    except:
        return None
    nodes = dev.device_node.split('/')
    return {'bus': int(nodes[-2]), 'address': int(nodes[-1])}
    
def symlinkToUsbDevice(symlink):
    '''
    Find the usb device associated with a symlink. Returns None if not found
    '''
    try:
        busAddress = symlinkToBusAddress(symlink)
        if not busAddress:
            return None
        return usb.core.find(**busAddress) #The search uses kwargs, so just convert the returned dict
    except:
        return None
    
def openDevice(symlink):
    '''
    open device and get the endpoints. returns a dict with device, and both endpoints
    '''
    dev = symlinkToUsbDevice(symlink)

def closeDevice(deviceInfo):
    dev = deviceInfo['device']
    usb.util.release_interface(dev, 0) #maybe not required to claim and release, but it can't hurt
    usb.util.dispose_resources(dev) #would get cleaned up anyway

#does this need to be called        self.usbContext.exit()
        

def main():
    devInfo = openDevice('usb-chip')
    
    print dev
    closeDevice(dev)
    print "done"

#------------------------------------------------------------------
if __name__ == "__main__":
#------------------------------------------------------------------
    exit( main() )
    

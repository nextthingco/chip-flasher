'''
Created on Mar 15, 2017

@author: howie
'''
import sys
import usb.core
from config import VERBOSE, POLLING_TIMEOUT
import time
from usbFactory import symlinkToBusAddress

FEL_VENDOR_ID=0x1f3a
FEL_PRODUCT_ID=0xefe8
FASTBOOT_VENDOR_ID=0x1f3a
FASTBOOT_PRODUCT_ID=0x1010

POLLING_DELAY_BETWEEN_RETRY = 1 # in seconds. cannot be 0
POLLING_RETRIES = POLLING_TIMEOUT / POLLING_DELAY_BETWEEN_RETRY
POLLING_NO_TIMEOUT = sys.maxsize
USB_TIMEOUT = 0 # 0 is unlimited

CHIP_USB_INTERFACE = 0

USB_RETRY_DELAY = 1
USB_RETRY_ATTEMPTS = 3

FASTBOOT_RESULT_LENGTH=64
FASTBOOT_OK_RESPONSE = 'OKAY'


TRACE_USB = False #used to dump bytes sent over USB to compare to sunxi-fel
dumpCount = 0
def dump(buf):
    '''
    Utility function used when debugging to dump a buffer as hex bytes
    :param buf:
    '''
    if len(buf) > 64:
        return 'big'
    
    res = ''
    for c in buf:
        res += "{:02x}".format(ord(c))
    return res

def dumps(buf):
    '''
    Utility function used when debugging to dump a string as hex bytes
    :param buf:
    '''
    if len(buf) > 64:
        return 'big'
    res = ''
    for c in buf:
        res += "{:02x}".format(c)
    return res

class DeviceException(Exception):
    '''
    Exception class for errors in DevicePort transfers
    '''
    def __init__(self,*args,**kwargs):
        Exception.__init__(self,*args,**kwargs)
        
class DevicePort(object):
    '''
    Class to manage a port and the device that is plugged in/removed
    '''
    __slots__ = ('device','deviceDescriptor','onFelCallback','inEp','outEp','writeCount') #using slots prevents bugs where members are created by accident
    def __init__(self, deviceDescriptor, onFelCallback):
        self.deviceDescriptor = deviceDescriptor
        self.device = None
        self.inEp = None
        self.outEp = None
        self.onFelCallback = onFelCallback
        self.writeCount = 0
    
    def findEndpoints(self, dev):
        '''
        Find the interface's endpoints for read and write. Currently assuming interface 0. May change for other SOCs, so would need
        to iterate over the interfaces to find the bulk endpoint. See c or javascript versions for this
        :param dev: The usb device
        '''
        #This is pretty much taken from the pyusb site
        dev.set_configuration()
        cfg = dev.get_active_configuration()
        usb.util.claim_interface(dev, CHIP_USB_INTERFACE)
        intf = cfg[(0,0)]

        self.inEp = usb.util.find_descriptor(intf, custom_match=lambda e: \
            usb.util.endpoint_direction(e.bEndpointAddress) == \
            usb.util.ENDPOINT_IN)
    
        self.outEp = usb.util.find_descriptor(intf, custom_match=lambda e: \
            usb.util.endpoint_direction(e.bEndpointAddress) == \
            usb.util.ENDPOINT_OUT)

    def waitForDisconnect(self):
        '''
        Poll until when no FEL or FASTBOOT is detected. Eventually add in SERIAL or ETHERNET too
        '''
        while True:
            found = False
            for dev in [self.deviceDescriptor.fel, self.deviceDescriptor.fastboot]:
                if symlinkToBusAddress(dev):
                    found = True
            if not found:
                break
            time.sleep(.2)
            

    def isNewState(self, vid, pid):
        '''
        Is the vid/pid state different from the current one?
        :param vid:
        :param pid:
        '''
        return not (self.device and self.device.idVendor == vid and self.device.idProduct == pid)
        
    def waitForState(self, vid, pid, timeout=POLLING_RETRIES):
        '''
        Wait for the device (or more accurately, a physical device plugged into the usb port) to be in a vid/pid state
        :param vid:
        :param pid:
        :param timeout: How long to wait before giving up. 
        '''
        if not self.isNewState(vid,pid):
            return False
        self.releaseDevice()
        if vid == FEL_VENDOR_ID and pid == FEL_PRODUCT_ID:
            symlink = self.deviceDescriptor.fel
        elif vid == FASTBOOT_VENDOR_ID and pid == FASTBOOT_PRODUCT_ID:
            symlink = self.deviceDescriptor.fastboot

        if VERBOSE:
            print 'WAITING for {} {:02x}:{:02x} '.format(symlink,vid, pid)
        for _ in xrange(1,timeout):
#             self.deviceAddress:
            deviceAddress = symlinkToBusAddress(symlink) #populates bus and address only
            if deviceAddress:
                deviceAddress['idVendor'] = vid
                deviceAddress['idProduct'] = pid
                device = usb.core.find(**deviceAddress) #The search uses kwargs, so just convert the returned dict
                if device:
                    try:
                        self.findEndpoints(device)
                    except Exception, e:
                        print "Error trying to set endpoints",e
                        print "Is another instance of this program running?"
                        raise e
                    else:
                        self.device = device
                        if symlink == self.deviceDescriptor.fel:
                            self.onFelCallback()
                        if VERBOSE:
                            print 'found device', deviceAddress
                        return True

                        
#             if VERBOSE:
#                 print 'try ',i
            time.sleep(POLLING_DELAY_BETWEEN_RETRY)
        
        raise DeviceException("Timeout waiting for vid:pid {:02x}:{:02x}".format(vid, pid))
    
    def readFastbootVariable(self, variable):
        '''
        Read a variable from fastboot. Currently not using this, but it does work
        :param variable: the variable to read from fastboot  e.g. 'serialno'
        '''
        self.usbWrite("getvar:"+ variable)
        result = self.usbReadString(FASTBOOT_RESULT_LENGTH)
        if not result or not result.startswith(FASTBOOT_OK_RESPONSE):
            return None
        else:
            return result[len(FASTBOOT_OK_RESPONSE):]
        
    def readAndVerify(self, data, dataLength):
        '''
        Read bytes from a file and compare to the data passed in
        :param data: Bytes that we are expecting to read
        :param dataLength: Length of bytes to read
        '''
        readBuffer = self.read(dataLength) # raw read, not comparing result
        for i, c in enumerate(data):
            if i >= len(readBuffer):
                break
            if readBuffer[i] != ord(c):
                raise DeviceException('Bad read back')
        return True

    def read(self, dataLength):
        '''
        Bulk read bytes from usb
        :param dataLength: How many bytes to read
        '''
        result = self.inEp.read(dataLength, USB_TIMEOUT)
        if TRACE_USB:
            global dumpCount
            dumpCount = dumpCount+1
            print '{}--- usbRead({}) = {}'.format(dumpCount, dataLength, dumps(result))
        return result
        
    def readString(self,dataLength):
        '''
        Read bytes from usb and convert to a string
        :param dataLength: How many bytes to read
        '''
#         print("{}: usb read {}".format(self.deviceDescriptor.uid, dataLength))
        resultBuffer = self.read(dataLength) # raw read, not comparing result
        return ''.join((chr(c) for c in resultBuffer)) #convert the buffer into a string using a generator comprehension

    def write(self, data, dataLength = None):
        '''
        Bulk write bytes to usb
        :param data: Bytes to write
        :param dataLength: Length of bytes. If not set, then it will be calculated
        '''
        if dataLength is None:
            dataLength = len(data)
        if TRACE_USB:
            global dumpCount
            dumpCount = dumpCount+1
            print '{}--- usbWrite({},{})'.format(dumpCount,dataLength, dump(data))
    
        try:
            return self.outEp.write(data, USB_TIMEOUT)
        except Exception,e:
            print("{}: usb error write #{}, {}".format(self.deviceDescriptor.uid, self.writeCount,dataLength))
            raise e            

        
    def releaseDevice(self):
        '''
        Release the resources associated with the device
        '''
        if self.device:
            try:
                usb.util.release_interface(self.device, CHIP_USB_INTERFACE) #maybe not required to claim and release, but it can't hurt
            except:
                pass # unplugging can cause weird state, so just ignore it
            try:
                usb.util.dispose_resources(self.device) #would get cleaned up anyway
            except:
                pass # unplugging can cause weird state, so just ignore it

        self.device = None
        self.inEp = None
        self.outEp = None


'''
Created on Mar 15, 2017

@author: howie
'''
import usb.core
import json
from struct import unpack
from collections import namedtuple
import time
from usbFactory import symlinkToBusAddress
from pprint import pprint
import datetime


# typedef struct CommandHeader {
#     unsigned int argument; // put this first in case of it being a magic number
#     unsigned char command;
#     unsigned char compressed;
#     unsigned char version;
#     unsigned char reserved; // for future use
#     unsigned int dataLength;
# } CommandHeaderType;

MAGIC_COMMAND = 0
COMMENT_COMMAND = 1
READ_COMMAND = 2
WRITE_COMMAND = 3
USLEEP_COMMAND = 4
MANIFEST_COMMAND = 5
FEL_WRITE_COMMAND = 6
FEL_READ_COMMAND = 7
FEL_EXE_COMMAND = 8

COMMAND_HEADER_TYPE_FMT = '<IBBBBI'
SIZEOF_HEADER = 12

FEL_VENDOR_ID=0x1f3a
FEL_PRODUCT_ID=0xefe8
FASTBOOT_VENDOR_ID=0x1f3a
FASTBOOT_PRODUCT_ID=0x1010

POLLING_TIMEOUT = 20 #in seconds
USB_TIMEOUT = 0; # 0 is unlimited

CHIP_USB_INTERFACE = 0

VERBOSE = True

CommandHeaderType = namedtuple('Header', 'argument command compressed version reserved dataLength')


def extract_header(record):
    return CommandHeaderType._make(unpack(COMMAND_HEADER_TYPE_FMT, record))
    

usleep = lambda x: time.sleep(x/1000000.0)

class FlashException(Exception):
    def __init__(self,*args,**kwargs):
        Exception.__init__(self,*args,**kwargs)
        
class ChpFlash(object):
    __slots__ = ('deviceDescriptor','chpFileName','device','inEp','outEp') #using slots prevents bugs where members are created by accident
    def __init__(self, deviceDescriptor, chpFileName):
        self.deviceDescriptor = deviceDescriptor
        self.chpFileName = chpFileName
        self.device = None
        self.inEp = None
        self.outEp = None
    
    def findEndpoints(self, dev):
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

    def waitForState(self, vid, pid):
        if self.device and self.device.idVendor == vid and self.device.idProduct == pid:
            if VERBOSE:
                print 'Using existing device {:02x}:{:02x}'.format(vid, pid)
            return
        if vid == FEL_VENDOR_ID and pid == FEL_PRODUCT_ID:
            symlink = self.deviceDescriptor.fel
        elif vid == FASTBOOT_VENDOR_ID and pid == FASTBOOT_PRODUCT_ID:
            symlink = self.deviceDescriptor.fastboot

        if VERBOSE:
            print 'WAITING for {} {:02x}:{:02x} '.format(symlink,vid, pid)
        for i in range(1,POLLING_TIMEOUT):
#             self.deviceAddress:
            deviceAddress = symlinkToBusAddress(symlink) #populates bus and address only
            if deviceAddress:
                deviceAddress['idVendor'] = vid
                deviceAddress['idProduct'] = pid
                self.device = usb.core.find(**deviceAddress) #The search uses kwargs, so just convert the returned dict
                if self.device:
                    self.findEndpoints(self.device)
                    if VERBOSE:
                        print 'found device', deviceAddress
                    return
            if VERBOSE:
                print 'try ',i
            time.sleep(1)
        

        raise FlashException("Timeout waiting for vid:pid {:02x}:{:02x}".format(vid, pid))
    
    def processComment(self, data):
        if VERBOSE:
            print data

    def processManifest(self, data):
        obj = json.loads(data)
        if VERBOSE:
            print 'Manifest:'
            pprint(obj)
        
    def usbRead(self, data, dataLength):
        readBuffer = self.inEp.read(dataLength, USB_TIMEOUT)
        for i, c in enumerate(data):
            if i >= len(readBuffer):
                break
            if readBuffer[i] != ord(c):
                raise FlashException('Bad read back')
        return True

    def usbWrite(self, data, dataLength):
        self.outEp.write(data,USB_TIMEOUT)

    def flash(self):
        totalBytes = 0
        processedBytes = 0
        startTime = time.time()
        try:
            with open(self.chpFileName, 'rb') as chp:
                while True:
                    headerBytes = chp.read(SIZEOF_HEADER)
                    if not headerBytes:
                        break
                    processedBytes += SIZEOF_HEADER
                    header = extract_header(headerBytes)
                    if not totalBytes: #set initial value
                        totalBytes = header.dataLength
                    cmd = header.command
                    if cmd == MAGIC_COMMAND:
                        pid = header.argument & 0xffff
                        vid = header.argument >> 16
                        self.waitForState(vid, pid)
                    elif cmd == USLEEP_COMMAND:
                        usleep(header.argument / 1000)
                    else: #data commands
                        dataLength = header.dataLength
                        data = chp.read(dataLength)
                        if cmd == COMMENT_COMMAND:
                            self.processComment(data)
                        elif cmd == READ_COMMAND:
                            self.usbRead(data, dataLength)
                        elif cmd == WRITE_COMMAND:
                            self.usbWrite(data, dataLength)
                        elif cmd == MANIFEST_COMMAND:
                            self.processManifest(data)
                        else:
                            print 'Unsupported command type', cmd
                            
                        processedBytes += header.dataLength 
        finally:
            if self.device:
                usb.util.release_interface(self.device, CHIP_USB_INTERFACE) #maybe not required to claim and release, but it can't hurt
                usb.util.dispose_resources(self.device) #would get cleaned up anyway
        
        elapsedTime = time.time() - startTime
        if VERBOSE:
            print 'Time: {} Processed {} bytes of {}'.format(datetime.timedelta(seconds=elapsedTime), processedBytes, totalBytes)
        

def flash(deviceDescriptor, chp):
    flasher = ChpFlash(deviceDescriptor,chp)
    flasher.flash()

from threading import Thread

def main():
#     chp = '/home/howie/Downloads/stable-chip-pro-blinkenlights-b1-Toshiba_512M_SLC.chp'
#     chp = '/home/howie/Downloads/stable-gui-b149-nl-Hynix_8G_MLC.chp'
    chp = '/home/howie/Downloads/gui43.chp'
    DD = namedtuple('DeviceDescriptor','fel fastboot')
    
    ports = [DD(fel='chip-{}-1-fel'.format(i+1), fastboot='chip-{}-1-fastboot'.format(i+1)) for i in range(3)]
    threads = []
    for port in ports:
        thread = Thread(target = flash, args = (port, chp))
        thread.start()
        threads.append(thread)
    
    
#         thread.join()
#------------------------------------------------------------------
if __name__ == "__main__":
#------------------------------------------------------------------
    exit( main() )
    

'''
Created on Mar 15, 2017

@author: howie
'''
import sys
import usb.core
import json
from struct import unpack
from collections import namedtuple
import time
from usbFactory import symlinkToBusAddress
from pprint import pprint
import datetime
from math import floor
from multiprocessing import Process, Queue, Pipe
from ui_strings import *
from runState import RunState

MAGIC_COMMAND = 0
COMMENT_COMMAND = 1
READ_COMMAND = 2
WRITE_COMMAND = 3
USLEEP_COMMAND = 4
MANIFEST_COMMAND = 5
FEL_WRITE_COMMAND = 6
FEL_READ_COMMAND = 7
FEL_EXE_COMMAND = 8


FEL_VENDOR_ID=0x1f3a
FEL_PRODUCT_ID=0xefe8
FASTBOOT_VENDOR_ID=0x1f3a
FASTBOOT_PRODUCT_ID=0x1010

# crunch's ethernet gadget is 2dfe:beef
POLLING_TIMEOUT = 20 #in seconds
USB_TIMEOUT = 0; # 0 is unlimited

CHIP_USB_INTERFACE = 0

VERBOSE = True

DONT_SEND_FASTBOOT_CONTINUE = True
# typedef struct CommandHeader {
#     unsigned int argument; // put this first in case of it being a magic number
#     unsigned char command;
#     unsigned char compressed;
#     unsigned char version;
#     unsigned char reserved; // for future use
#     unsigned int dataLength;
# } CommandHeaderType;
COMMAND_HEADER_TYPE_FMT = '<IBBBBI'
SIZEOF_HEADER = 12
CommandHeaderType = namedtuple('Header', 'argument command compressed version reserved dataLength')
def extract_header(record):
    return CommandHeaderType._make(unpack(COMMAND_HEADER_TYPE_FMT, record))
    

usleep = lambda x: time.sleep(x/1000000.0)

class FlashException(Exception):
    def __init__(self,*args,**kwargs):
        Exception.__init__(self,*args,**kwargs)
        
class ChpFlash(object):
    __slots__ = ('progressQueue', 'connectionFromParent', 'deviceDescriptor','chpFileName','device','inEp','outEp') #using slots prevents bugs where members are created by accident
    def __init__(self, progressQueue, connectionFromParent, args):
#     deviceDescriptor, chpFileName):
        self.progressQueue = progressQueue
        self.connectionFromParent = connectionFromParent
        self.deviceDescriptor = args['deviceDescriptor']
        self.chpFileName = args['chpFileName']
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

    def waitForDisconnect(self):
        while True:
            found = False
            for dev in [self.deviceDescriptor.fel, self.deviceDescriptor.fastboot]:
                if symlinkToBusAddress(dev):
                    found = True
            if not found:
                break
            time.sleep(.2)
            
        
    def waitForState(self, vid, pid, timeout=POLLING_TIMEOUT):
        if self.device and self.device.idVendor == vid and self.device.idProduct == pid:
            if VERBOSE:
                print 'Using existing device {:02x}:{:02x}'.format(vid, pid)
            return
        self.releaseDevice()
        fastboot = False
        if vid == FEL_VENDOR_ID and pid == FEL_PRODUCT_ID:
            symlink = self.deviceDescriptor.fel
        elif vid == FASTBOOT_VENDOR_ID and pid == FASTBOOT_PRODUCT_ID:
            symlink = self.deviceDescriptor.fastboot
            fastboot = True

        if VERBOSE:
            print 'WAITING for {} {:02x}:{:02x} '.format(symlink,vid, pid)
        for _ in xrange(1,timeout):
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
                    if fastboot:
                        self.onFastbootFound()
                    return
#             if VERBOSE:
#                 print 'try ',i
            time.sleep(1)
        

        raise FlashException("Timeout waiting for vid:pid {:02x}:{:02x}".format(vid, pid))
    
    def onFastbootFound(self):
        '''
        Maybe read serial number and save it off?
        '''
        print ('Fastboot Found')
        
#         self.usbWrite('getvar:serialNo')

    def processComment(self, data):
        if VERBOSE:
            print data
        errorCode = 202 #at this point, we've detected the device, so it's either a 202 or 203
        stage = None
        if 'fastboot' in data:
            if 'continue' in data:
                errorCode = None
                stage = PASS_TEXT
            elif 'spl' in data:
                stage = UI_UPLOAD_SPL 
            elif 'uboot' in data:
                stage = UI_UPLOAD_UBOOT
            elif 'UBI' in data:
                errorCode = 203
                stage = UI_UPLOAD_UBI 
        else:
            if 'u-boot' in data:
                stage =  UI_EXECUTE_UBOOT_SCRIPT
            elif 'spl' in data:
                stage = UI_UPLOAD_SPL # not used anymore for CHIP Pro
        return stage, errorCode        

    def processManifest(self, data):
        obj = json.loads(data)
        return obj
        
    def usbRead(self, data, dataLength):
        readBuffer = self.inEp.read(dataLength, USB_TIMEOUT)
        for i, c in enumerate(data):
            if i >= len(readBuffer):
                break
            if readBuffer[i] != ord(c):
                raise FlashException('Bad read back')
        return True

    def usbWrite(self, data, dataLength):
        self.outEp.write(data, USB_TIMEOUT)

    def read(self):
        '''
        Generator which reads the file and yields records of header, data
        '''
        with open(self.chpFileName, 'rb') as chp:
            while True:
                headerBytes = chp.read(SIZEOF_HEADER)
                if not headerBytes:
                    break
                header = extract_header(headerBytes)
                data = None
                if header.command not in [MAGIC_COMMAND, USLEEP_COMMAND]:
                    data = chp.read(header.dataLength)
                yield header,data

                    
    def readManifest(self):
        totalBytes = 0
        for header,data in self.read():
            cmd = header.command
            if cmd == MAGIC_COMMAND:
                if not totalBytes: #set initial value
                    totalBytes = header.dataLength
            elif cmd == MANIFEST_COMMAND:
                manifest = self.processManifest(data)
                manifest['totalBytes'] = totalBytes
                if VERBOSE:
                    print 'Manifest:'
                    pprint(manifest)
                return manifest
        return None
        
    def releaseDevice(self):
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

    def flash(self):
        errorCode = 201 #Hard coded 201 is an error in not detecting the device (timeout)
        stage = UI_WAITING_FOR_DEVICE
        state = WAITING_TEXT
        self.notifyProgress({'runState': RunState.PASSIVE_STATE, 'stage': stage, 'state': state})
        self.waitForStartTrigger() #This may just fall through if not using a button trigger
        self.notifyProgress({'runState': RunState.ACTIVE_STATE, 'state': RUNNING_TEXT})
        totalBytes = 0
        processedBytes = 0
        percentComplete = 0
        done = False
        startTime = time.time()
        self.releaseDevice()

        try:
            for header,data in self.read():
                processedBytes += SIZEOF_HEADER
                if not totalBytes: #set initial value
                    totalBytes = header.dataLength
                cmd = header.command
                if cmd == MAGIC_COMMAND:
                    pid = header.argument & 0xffff
                    vid = header.argument >> 16
                    self.waitForState(vid, pid)
                    if state is not FLASHING_TEXT: #if we got here, then we're about to start writing data
                        state = FLASHING_TEXT
                        self.notifyProgress({'state':state})
                elif cmd == USLEEP_COMMAND:
                    usleep(header.argument / 1000)
                else: #data commands
                    dataLength = header.dataLength
                    if cmd == COMMENT_COMMAND:
                        newStage, errorCode = self.processComment(data)
                        if DONT_SEND_FASTBOOT_CONTINUE and newStage is PASS_TEXT:
                            done = True
                            if VERBOSE:
                                print ('stopping after receiving a fastboot continue')
                        if newStage is not stage:
                            stage = newStage
                            self.notifyProgress({'stage': stage})
                    elif cmd == READ_COMMAND:
                        self.usbRead(data, dataLength)
                    elif cmd == WRITE_COMMAND:
                        self.usbWrite(data, dataLength)
                    elif cmd == MANIFEST_COMMAND: #manifest needs to be before any reads/writes in the chp file for manifestInfoOnly to behave properly
                        manifest = self.processManifest(data)
                    else:
                        print 'Unsupported command type', cmd
                    if done:
                        newPercent = 100.0
                    else:
                        processedBytes += header.dataLength
                        newPercent = floor(100 * processedBytes / totalBytes)
                        
                    if newPercent != percentComplete:
#                         print 'Device {} percent complete {}'.format(self.deviceDescriptor.uid, newPercent)
                        percentComplete = newPercent
                        self.notifyProgress({'percent': percentComplete})
                    if done:
                        break
        except Exception,e:
            if VERBOSE:
                print "exception",e
            self.notifyProgress({'runState': RunState.FAIL_STATE, 'errorCode': errorCode, 'state': FAIL_TEXT})
        else:
            self.notifyProgress({'runState': RunState.PASS_STATE,'stage': stage})
        finally:
            self.releaseDevice()
        
        elapsedTime = time.time() - startTime
        if VERBOSE:
            print 'Time: {} Processed {} bytes of {}'.format(datetime.timedelta(seconds=elapsedTime), processedBytes, totalBytes)

    def notifyProgress(self, progress):
        if self.progressQueue:
            progress['uid'] = self.deviceDescriptor.uid
            self.progressQueue.put(progress)
    
    def waitForStartTrigger(self):
        if self.connectionFromParent: #if parent sends messages to start... flashing below is allowed fail waiting for FEL
            while self.connectionFromParent.poll(): # clear out any pending stuff
                print 'discarding',self.connectionFromParent.recv()
            print 'child received',self.connectionFromParent.recv() #now block until a message
        else: #if not waiting for click, wait for FEL indefinitely
            self.waitForState(FEL_VENDOR_ID, FEL_PRODUCT_ID, sys.maxsize)
            
    def flashForever(self):
        try:
            while True:
                self.flash()
                self.waitForDisconnect()
                self.notifyProgress({'runState': RunState.DISCONNECTED_STATE, 'state': DISCONNECTED_TEXT})
        except KeyboardInterrupt:
            pass


def flash(progressQueue, connectionFromParent, args):
    flasher = ChpFlash(progressQueue, connectionFromParent, args)
    manifest = flasher.flash(True)
    pprint(manifest)
    flasher.flashForever()


def main():
    chp = '/home/howie/Downloads/stable-chip-pro-blinkenlights-b1-Toshiba_512M_SLC.chp'
#     chp = '/home/howie/Downloads/stable-gui-b149-nl-Hynix_8G_MLC.chp'
#     chp = '/home/howie/Downloads/gui43.chp'
    DD = namedtuple('DeviceDescriptor','uid fel fastboot')
    args = {'chpFileName': chp}
    ports = [DD(uid=i+1, fel='chip-{}-1-fel'.format(i+1), fastboot='chip-{}-1-fastboot'.format(i+1)) for i in range(1)]
    procs = []
    progressQueue = Queue()
    
    connections = []
    for port in ports:
        parent_conn, connectionFromParent = Pipe()
#         parent_conn = None
#         connectionFromParent = None
        connections.append(parent_conn)
        args['deviceDescriptor'] = port
        proc = Process(target = flash, args = (progressQueue, connectionFromParent, args))
        proc.start()
        procs.append(proc)
    
    i = 0
    while True:
        i = i +1
        while not progressQueue.empty():
            progress = progressQueue.get()
            print progress
        time.sleep(.1)
        if i % 50 == 0:
            for con in connections:
                if con:
                    con.send("start")
            
    
    
#         thread.join()
#------------------------------------------------------------------
if __name__ == "__main__":
#------------------------------------------------------------------
    exit( main() )
    

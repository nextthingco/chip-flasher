'''
Created on Mar 15, 2017

@author: howie
'''
import sys
import usb.core
import json
from struct import unpack, pack
from collections import namedtuple
import time
from usbFactory import symlinkToBusAddress
from pprint import pprint
import datetime
from math import floor
from multiprocessing import Process, Queue, Pipe
from ui_strings import *
from runState import RunState
import traceback
from config import VERBOSE


USB_TIMEOUT = 0; # 0 is unlimited

CHIP_USB_INTERFACE = 0

class UsbDevice(object):
    __slots__ = ('dev', 'inEp','outEp') #using slots prevents bugs where members are created by accident
    def __init__(self, progressQueue, connectionFromParent, args):
        self.dev = None
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
            

    def isNewState(self, vid, pid):
        return not (self.device and self.device.idVendor == vid and self.device.idProduct == pid)
        
    def waitForState(self, vid, pid, timeout=POLLING_TIMEOUT):
        if not self.isNewState(vid,pid):
            return False
        self.releaseDevice()
        fastboot = False
        fel = False
        if vid == FEL_VENDOR_ID and pid == FEL_PRODUCT_ID:
            symlink = self.deviceDescriptor.fel
            fel = True
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
                    elif fel:
                        self.onFelFound()
                    return True
#             if VERBOSE:
#                 print 'try ',i
            time.sleep(1)
        

        raise FlashException("Timeout waiting for vid:pid {:02x}:{:02x}".format(vid, pid))
    
    def onFelFound(self):
        self.serialNumber = getSerialNumber(self)
        if VERBOSE:
            print "serial number read from FEL" + self.serialNumber
            
    def onFastbootFound(self):
        '''
        Read serial number and save it off?
        '''
        self.usbWrite("getvar:serialno")
        result = self.usbReadString(FASTBOOT_RESULT_LENGTH)
        if not result or not result.startswith(FASTBOOT_OK_RESPONSE):
            self.serialNumber = None
        else:
            self.serialNumber = result[len(FASTBOOT_OK_RESPONSE):]
        
    
#         self.usbWrite('getvar:serialNo')

    def processComment(self, data):
        if VERBOSE:
            print data
        errorNumber = 202 #at this point, we've detected the device, so it's either a 202 or 203
        stage = None
        if 'fastboot' in data:
            if 'continue' in data:
                errorNumber = None
                stage = PASS_TEXT
            elif 'spl' in data:
                stage = UI_UPLOAD_SPL 
            elif 'uboot' in data:
                stage = UI_UPLOAD_UBOOT
            elif 'UBI' in data:
                errorNumber = 203
                stage = UI_UPLOAD_UBI 
        else:
            if 'u-boot' in data:
                stage =  UI_EXECUTE_UBOOT_SCRIPT
            elif 'spl' in data:
                stage = UI_UPLOAD_SPL # not used anymore for CHIP Pro
        return stage, errorNumber        

    def processManifest(self, data):
        obj = json.loads(data)
        return obj
        
    def usbReadAndVerify(self, data, dataLength):
        readBuffer = self.usbRead(dataLength) # raw read, not comparing result
        for i, c in enumerate(data):
            if i >= len(readBuffer):
                break
            if readBuffer[i] != ord(c):
                raise FlashException('Bad read back')
        return True

    def usbRead(self, dataLength):
        return self.inEp.read(dataLength, USB_TIMEOUT)
        
    def usbReadString(self,dataLength):
        resultBuffer = self.usbRead(dataLength) # raw read, not comparing result
        return ''.join((chr(c) for c in resultBuffer)) #convert the buffer into a string using a generator comprehension

    def usbWrite(self, data, dataLength = None):
        if dataLength is None:
            dataLength = len(data)
        return self.outEp.write(data, USB_TIMEOUT)

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
        errorNumber = 201 #Hard coded 201 is an error in not detecting the device (timeout)
        stage = WAITING_TEXT
        state = WAITING_TEXT
        self.serialNumber = None
        output=''
        self.notifyProgress({'progress': 0, 'runState': RunState.PASSIVE_STATE, 'stage': stage, 'state': state, 'output':output})
        self.waitForStartTrigger() #This may just fall through if not using a button trigger

        
        startTime = time.time()
        stage = UI_WAITING_FOR_DEVICE
        state = RUNNING_TEXT
        output = 'Start: ' + time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime())
        self.notifyProgress({'runState': RunState.ACTIVE_STATE, 'state': state, 'stage':stage, 'output':output})
        totalBytes = 0
        processedBytes = 0
        percentComplete = 0
        done = False
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
                    if self.isNewState(vid, pid):
                        output += '\nWaiting for USB Device {:02x}:{:02x}'.format(vid, pid)
                        self.notifyProgress({'output':output})
                    self.waitForState(vid, pid)
                    if state is not FLASHING_TEXT: #if we got here, then we're about to start writing data
                        state = FLASHING_TEXT
                        self.notifyProgress({'state':state})
                elif cmd == USLEEP_COMMAND:
                    usleep(header.argument / 1000)
                else: #data commands
                    dataLength = header.dataLength
                    if cmd == COMMENT_COMMAND:
                        newStage, errorNumber = self.processComment(data)
                        if DONT_SEND_FASTBOOT_CONTINUE and newStage is PASS_TEXT:
                            done = True
                            output += '\n'+ data + "\nDone (continue ignored to avoid booting)"
                        elif newStage is not stage:
                            output += '\n' + data
                            stage = newStage
                            self.notifyProgress({'stage': stage,'output':output})
                    elif cmd == READ_COMMAND:
                        self.usbReadAndVerify(data, dataLength)
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
                        percentComplete = newPercent
                        self.notifyProgress({'progress': percentComplete/100.0})
                    if done:
                        break
        except Exception,e:
            elapsedTime = time.time() - startTime
            if VERBOSE:
                print "exception",repr(e)
                traceback.print_exc()
            output += '\n' + repr(e)
            output += '\n' + traceback.format_exc(e)
            output += "\nProcessed {} bytes of {}".format(processedBytes, totalBytes)
            self.notifyProgress({'runState': RunState.FAIL_STATE, 'errorNumber': errorNumber, 'state': FAIL_TEXT, 'output': output, 'elapsedTime':elapsedTime, 'chipId': self.serialNumber, 'returnValues':{'image':self.chpFileName}})
        else:
            elapsedTime = time.time() - startTime

            output += '\nTotal Time {}'.format(datetime.timedelta(seconds=elapsedTime))
            self.notifyProgress({'runState': RunState.PASS_STATE,'stage': stage, 'output': output, 'elapsedTime':elapsedTime ,'chipId': self.serialNumber, 'returnValues':{'image':self.chpFileName}}) #eventually write manifest too
        finally:
            self.releaseDevice()
        return True

    def notifyProgress(self, progress):
        if self.progressQueue:
            progress['uid'] = self.deviceDescriptor.uid
            self.progressQueue.put(progress)
    
    def waitForStartTrigger(self):
        if self.connectionFromParent: #if parent sends messages to start... flashing below is allowed fail waiting for FEL
            while self.connectionFromParent.poll(): # clear out any pending stuff
                self.connectionFromParent.recv()
            self.connectionFromParent.recv() #now block until a message
#         else: #if not waiting for click, wait for FEL indefinitely
        self.waitForState(FEL_VENDOR_ID, FEL_PRODUCT_ID, sys.maxsize)
            
    def flashForever(self):
        while True:
            try:
                self.flash()
                self.waitForDisconnect()
                self.notifyProgress({'progress':0, 'runState': RunState.DISCONNECTED_STATE, 'state': DISCONNECTED_TEXT})
            except KeyboardInterrupt:
                return
#             except Exception,e:
#                 print 'Ignoring ' , repr(e)

    @staticmethod
    def statsTableName():
        return "flash"

    CUSTOM_COLUMNS = [
                      ['image','TEXT',""]
                    ]

    @classmethod
    def statsTableColumns(cls):
        return cls.CUSTOM_COLUMNS

    @staticmethod
    def getStatsQueries(where):
        table = ChpFlash.statsTableName()
        return [
            "select count(*) as 'total', sum(1-result) as 'failed', sum(result) as 'passed' from {0} where {1}".format(table,where),
            "select avg(elapsedTime) as 'averageTime' from {0} where result=1 AND {1}".format(table,where),
            "select error as errors_key, count(error) as errors_val from {0} where error != 0 and {1} group by error order by error".format(table,where)
        ]



def flash(progressQueue, connectionFromParent, args):
    flasher = ChpFlash(progressQueue, connectionFromParent, args)
    manifest = flasher.readManifest()
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
    

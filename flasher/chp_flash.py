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
from pprint import pprint, pformat
import datetime
from math import floor
from multiprocessing import Process, Queue, Pipe
from ui_strings import *
from runState import RunState
import traceback
from config import VERBOSE, AUTO_START_ON_DEVICE_DETECTION, FEL_SLEEP_MULTIPLIER
import fel
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
POLLING_DELAY_BETWEEN_RETRY = 1 # in seconds. cannot be 0
POLLING_RETRIES = POLLING_TIMEOUT / POLLING_DELAY_BETWEEN_RETRY
POLLING_NO_TIMEOUT = sys.maxsize
USB_TIMEOUT = 0 # 0 is unlimited

CHIP_USB_INTERFACE = 0

DONT_SEND_FASTBOOT_CONTINUE = True

USB_RETRY_DELAY = 1
USB_RETRY_ATTEMPTS = 3

FASTBOOT_RESULT_LENGTH=64
FASTBOOT_OK_RESPONSE = 'OKAY'

ERROR_DEVICE_NOT_FOUND = 201
ERROR_IN_SPL_OR_UBOOT = 202
ERROR_IN_FASTBOOT = 203
SUCCESS = 0

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

TRACE_USB = False #used to dump bytes sent over USB to compare to sunxi-fel
dumpCount = 0
def dump(buf):
    if len(buf) > 64:
        return 'big'
    
    res = ''
    for c in buf:
        res += "{:02x}".format(ord(c))
    return res

def dumps(buf):
    if len(buf) > 64:
        return 'big'
    res = ''
    for c in buf:
        res += "{:02x}".format(c)
    return res
        
class ChpFlash(object):
    __slots__ = ('progressQueue', 'connectionFromParent', 'lock', 'deviceDescriptor','chpFileName','device','inEp','outEp', 'serialNumber', 'output','writeCount') #using slots prevents bugs where members are created by accident
    def __init__(self, progressQueue, connectionFromParent, lock, args):
#     deviceDescriptor, chpFileName):
        self.progressQueue = progressQueue
        self.connectionFromParent = connectionFromParent
        self.lock = lock
        self.deviceDescriptor = args.get('deviceDescriptor') #optional if just reading manifest
        self.chpFileName = args['chpFileName']
        self.device = None
        self.inEp = None
        self.outEp = None
        self.serialNumber = None
        self.output = ''
        self.writeCount = 0
    
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
        
    def waitForState(self, vid, pid, timeout=POLLING_RETRIES):
        if not self.isNewState(vid,pid):
            return False
        self.releaseDevice(self.device)
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
                            self.onFoundFel()
                        if VERBOSE:
                            print 'found device', deviceAddress
                        return True

                        
#             if VERBOSE:
#                 print 'try ',i
            time.sleep(POLLING_DELAY_BETWEEN_RETRY)
        

        raise FlashException("Timeout waiting for vid:pid {:02x}:{:02x}".format(vid, pid))
    
    def onFoundFel(self):
        self.serialNumber = self.readSerialNumber()
        if self.serialNumber:
            self.notifyProgress({'output':self.output})

    def readFastbootVariable(self, variable):
        '''
        Read a variable from bastboot. e.g. 'serialno'
        '''
        self.usbWrite("getvar:"+ variable)
        result = self.usbReadString(FASTBOOT_RESULT_LENGTH)
        if not result or not result.startswith(FASTBOOT_OK_RESPONSE):
            return None
        else:
            return result[len(FASTBOOT_OK_RESPONSE):]

    def processComment(self, data):
        if VERBOSE:
            print data
        errorNumber = ERROR_IN_SPL_OR_UBOOT #at this point, we've detected the device, so it's either a 202 or 203
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
                errorNumber = ERROR_IN_FASTBOOT
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
        result = self.inEp.read(dataLength, USB_TIMEOUT)
        if TRACE_USB:
            global dumpCount
            dumpCount = dumpCount+1
            print '{}--- usbRead({}) = {}'.format(dumpCount, dataLength, dumps(result))
        return result
        
    def usbReadString(self,dataLength):
#         print("{}: usb read {}".format(self.deviceDescriptor.uid, dataLength))
        resultBuffer = self.usbRead(dataLength) # raw read, not comparing result
        return ''.join((chr(c) for c in resultBuffer)) #convert the buffer into a string using a generator comprehension

    def usbWrite(self, data, dataLength = None):
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
        
    def releaseDevice(self, device):
        if device:
            try:
                usb.util.release_interface(device, CHIP_USB_INTERFACE) #maybe not required to claim and release, but it can't hurt
            except:
                pass # unplugging can cause weird state, so just ignore it
            try:
                usb.util.dispose_resources(device) #would get cleaned up anyway
            except:
                pass # unplugging can cause weird state, so just ignore it

        self.device = None
        self.inEp = None
        self.outEp = None

    def flash(self):
        errorNumber = ERROR_DEVICE_NOT_FOUND #Hard coded 201 is an error in not detecting the device (timeout)
        stage = WAITING_TEXT
        state = WAITING_TEXT
        self.serialNumber = None
        self.output=''
        self.notifyProgress({'progress': 0, 'runState': RunState.PASSIVE_STATE, 'stage': stage, 'state': state, 'output':self.output})
        self.waitForStartTrigger() #This may just fall through if not using a button trigger
        
        startTime = time.time()
        stage = UI_WAITING_FOR_DEVICE
        state = RUNNING_TEXT
        self.output += '\nStart: ' + time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime())
        self.notifyProgress({'runState': RunState.ACTIVE_STATE, 'state': state, 'stage':stage, 'output':self.output})
        totalBytes = 0
        processedBytes = 0
        percentComplete = 0
        done = False
        self.writeCount = 0
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
                        self.output += '\nWaiting for USB Device {:02x}:{:02x}'.format(vid, pid)
                        self.notifyProgress({'output':self.output})
                    self.waitForState(vid, pid)
                    if state is not FLASHING_TEXT: #if we got here, then we're about to start writing data
                        state = FLASHING_TEXT
                        self.notifyProgress({'state':state})
                elif cmd == USLEEP_COMMAND:
                    amount = FEL_SLEEP_MULTIPLIER * header.argument / 1000000.0
                    if VERBOSE:
                        print "sleeping for " + str( amount)
                    time.sleep(amount)
                else: #data commands
                    dataLength = header.dataLength
                    if cmd == COMMENT_COMMAND:
                        newStage, errorNumber = self.processComment(data)
                        if DONT_SEND_FASTBOOT_CONTINUE and newStage is PASS_TEXT:
                            done = True
                            self.output += '\n'+ data + "\nDone (continue ignored to avoid booting)"
                        else:  #newStage is not stage:
                            self.output += '\n' + data
                            stage = newStage
                            self.notifyProgress({'stage': stage,'output':self.output})
                    elif cmd == READ_COMMAND:
                        self.usbReadAndVerify(data, dataLength)
                    elif cmd == WRITE_COMMAND:
                        self.writeCount = self.writeCount +1
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
            self.output += '\n' + repr(e)
            self.output += '\n' + traceback.format_exc(e)
            self.output += "\nProcessed {} bytes of {}".format(processedBytes, totalBytes)
            self.notifyProgress({'runState': RunState.FAIL_STATE, 'errorNumber': errorNumber, 'state': FAIL_WITH_ERROR_CODE_TEXT.format(errorNumber), 'output': self.output, 'elapsedTime':elapsedTime, 'chipId': self.serialNumber, 'returnValues':{'image':self.chpFileName}})
            return errorNumber
        else:
            elapsedTime = time.time() - startTime

            self.output += '\nTotal Time {}'.format(datetime.timedelta(seconds=elapsedTime))
            self.notifyProgress({'runState': RunState.PASS_STATE,'stage': stage, 'output': self.output, 'elapsedTime':elapsedTime ,'chipId': self.serialNumber, 'returnValues':{'image':self.chpFileName}}) #eventually write manifest too
        finally:
            self.releaseDevice(self.device)
        return SUCCESS

    def notifyProgress(self, progress):
        if self.progressQueue:
            progress['uid'] = self.deviceDescriptor.uid
            self.progressQueue.put(progress)
    
    def readSerialNumber(self):
        serialNumber = fel.getSerialNumber(self)
        if serialNumber:
            # now, call the parent process asking it for an existing record in its databse
            self.connectionFromParent.send({'findChipId':serialNumber})
            result = self.connectionFromParent.recv()
            if result:
                dataDict = result['findChipId']
                if dataDict:
                    self.output += '\n' + pformat(dataDict)
                else:
                    self.output += '\n' + "First Flash"
                return serialNumber
            else:
                print "shouldn't happen"
        else:
            print 'ERROR failed to read serial from FEL.'
        return None

    def waitForStartTrigger(self):
        if not AUTO_START_ON_DEVICE_DETECTION: #if parent sends messages to start... flashing below is allowed fail waiting for FEL
            while self.connectionFromParent.poll(): # clear out any pending stuff
                self.connectionFromParent.recv()
            self.connectionFromParent.recv() #now block until a message
            return True

        if self.waitForState(FEL_VENDOR_ID, FEL_PRODUCT_ID, POLLING_NO_TIMEOUT):
            serialNumber = self.readSerialNumber()
            if serialNumber:
                self.serialNumber = serialNumber
                self.notifyProgress({'output':self.output})
                return True
            
        return False
            
    def flashForever(self):
        while True:
            try:
                if self.flash() == ERROR_DEVICE_NOT_FOUND:
                    self.connectionFromParent.send({'clickMe':self.deviceDescriptor.uid})
                    click = self.connectionFromParent.recv() #now block until a message
                    if VERBOSE:
                        print "Received {}".format(click)

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
    if VERBOSE:
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
    

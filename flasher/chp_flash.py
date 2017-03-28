'''
Created on Mar 15, 2017

@author: howie
'''
import sys
import json
from struct import unpack
from collections import namedtuple
import time
from pprint import pprint
import datetime
from math import floor
from ui_strings import *
from runState import RunState
import traceback
from config import VERBOSE, AUTO_START_ON_DEVICE_DETECTION, FEL_SLEEP_MULTIPLIER, DONT_SEND_FASTBOOT_CONTINUE
import fel
from devicePort import DevicePort

#constants from the howitzer
MAGIC_COMMAND = 0
COMMENT_COMMAND = 1
READ_COMMAND = 2
WRITE_COMMAND = 3
USLEEP_COMMAND = 4
MANIFEST_COMMAND = 5
FEL_WRITE_COMMAND = 6
FEL_READ_COMMAND = 7
FEL_EXE_COMMAND = 8

#usb device vid/pids
FEL_VENDOR_ID=0x1f3a
FEL_PRODUCT_ID=0xefe8
FASTBOOT_VENDOR_ID=0x1f3a
FASTBOOT_PRODUCT_ID=0x1010

#no timeout is really a huge value
POLLING_NO_TIMEOUT = sys.maxsize

#Factory-defined error messages
ERROR_DEVICE_NOT_FOUND = 201
ERROR_IN_SPL_OR_UBOOT = 202
ERROR_IN_FASTBOOT = 203
SUCCESS = 0

# From extract.h in the howitzer. This defines the structure of the header blocks
# typedef struct CommandHeader {
#     unsigned int argument; // put this first in case of it being a magic number
#     unsigned char command;
#     unsigned char compressed;
#     unsigned char version;
#     unsigned char reserved; // for future use
#     unsigned int dataLength;
# } CommandHeaderType;
COMMAND_HEADER_TYPE_FMT = '<IBBBBI' #This is how to unpack the Commandheader
SIZEOF_HEADER = 12
CommandHeaderType = namedtuple('Header', 'argument command compressed version reserved dataLength')
def extract_header(record):
    '''
    Extract the command header bytes into a named tuple for easy processing
    :param record:
    '''
    return CommandHeaderType._make(unpack(COMMAND_HEADER_TYPE_FMT, record))
            
class ChpFlash(object):
    '''
    Main routine to flash a single CHIP from a .chp file. It loops through the file and processes the headers/data, sending and receiving data to/from the device
    '''
    __slots__ = ('progressQueue', 'connectionFromParent', 'lock', 'deviceDescriptor','devicePort', 'chpFileName','devicePort', 'serialNumber', 'output', 'history') #using slots prevents bugs where members are created by accident

    def __init__(self, progressQueue, connectionFromParent, lock, args):
        '''
        Constructor
        :param progressQueue: multiprocessing.Queue which will be sent progress updates
        :param connectionFromParent: From the Port that was created by the controller
        :param lock: Currently unused. Old flasher required a mutex, so thought it might be a useful placeholder for the future just in case
        :param args: Dictionary of args to pass along to the flasher. currently just the chp file name
        '''
        self.progressQueue = progressQueue
        self.connectionFromParent = connectionFromParent
        self.lock = lock
        self.deviceDescriptor = args.get('deviceDescriptor') #optional if just reading manifest
        self.chpFileName = args['chpFileName']
        self.devicePort = DevicePort(self.deviceDescriptor, self.onFoundFel.__get__(self,ChpFlash))
        self.serialNumber = None
        self.output = ''
        self.history = {}
    
    def processComment(self, data):
        '''
        Process the "comment" for the following .chp data. This lets us determine the stage we are in
        The comment is just the command line params passed into fel or fastboot
        :param data: String contents of the comment
        '''
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
        '''
        Handle the manifest entry. Since the manifest is read once at startup, there's nothing really needed at this point
        :param data: String with the manifest (encoded as json)
        '''
        obj = json.loads(data)
        return obj
        
    def read(self):
        '''
        Generator which reads the file and yields records of header, data
        '''
        with open(self.chpFileName, 'rb') as chp:
            while True:
                headerBytes = chp.read(SIZEOF_HEADER)
                if not headerBytes: #No more data, so break and finish the iterator
                    break
                header = extract_header(headerBytes)
                data = None
                if header.command not in [MAGIC_COMMAND, USLEEP_COMMAND]: #these two don't have associated data
                    data = chp.read(header.dataLength)
                yield header,data
                    
    def readManifest(self):
        '''
        Read the manifest from the file. This is only done once at startup to get info to display in file info tab
        '''
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
        
    def flash(self):
        '''
        The core function. It iterates over the data and handles the different kinds of actions (read, write, usleep, etc)
        It also keeps track of bytes written for progress and the current state/stage for updating the gui/database.
        TODO use an object to store progress instead of what's done below with sending dicts
        '''
        
        #Pre-flash Initialization
        errorNumber = ERROR_DEVICE_NOT_FOUND #Hard coded 201 is an error in not detecting the device (timeout)
        stage = WAITING_TEXT
        state = WAITING_TEXT
        self.serialNumber = None
        self.output=''
        self.history = {}
        self.notifyProgress({'progress': 0, 'runState': RunState.PASSIVE_STATE, 'stage': stage, 'state': state, 'output':self.output, 'history':self.history })
        
        self.waitForStartTrigger() #This may just fall through if not using a button trigger
        
        #Ok, now we know we've got a device, so let's start flashing
        #More initialization, now that we know we've got a device
        startTime = time.time()
        stage = UI_WAITING_FOR_DEVICE
        state = RUNNING_TEXT
        self.output += '\nStart: ' + time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime())
        self.notifyProgress({'runState': RunState.ACTIVE_STATE, 'state': state, 'stage':stage, 'output':self.output})
        totalBytes = 0
        processedBytes = 0
        percentComplete = 0
        done = False
        
        # Main loop here
        try:
            for header,data in self.read():
                processedBytes += SIZEOF_HEADER
                if not totalBytes: #set initial value
                    totalBytes = header.dataLength
                cmd = header.command
                #Now process the commands
                if cmd == MAGIC_COMMAND:
                    pid = header.argument & 0xffff
                    vid = header.argument >> 16
                    if self.devicePort.isNewState(vid, pid):
                        self.output += '\nWaiting for USB Device {:02x}:{:02x}'.format(vid, pid)
                        self.notifyProgress({'output':self.output})
                    self.devicePort.waitForState(vid, pid)
                    if state is not FLASHING_TEXT: #if we got here, then we're about to start writing data
                        state = FLASHING_TEXT
                        stateToShow = state
                        attempts = self.history.get('attempts')
                        if attempts and int(attempts) != 0:
                            stateToShow = FLASHING_TEXT_TEMPLATE.format(attempts)
                        self.notifyProgress({'state':stateToShow})
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
                        self.devicePort.readAndVerify(data, dataLength)
                    elif cmd == WRITE_COMMAND:
                        self.devicePort.write(data, dataLength)
                    elif cmd == MANIFEST_COMMAND: 
                        manifest = self.processManifest(data) #currently unused here
                    else:
                        print 'Unsupported command type', cmd #something weird in the .chp file
                    if done: #It's common that instead of exhausting the file, we arrive at done when we reach a fastboot continue.
                        newPercent = 100.0
                    else:
                        processedBytes += header.dataLength
                        newPercent = floor(100 * processedBytes / totalBytes)
                        
                    if newPercent != percentComplete:
                        percentComplete = newPercent
                        self.notifyProgress({'progress': percentComplete/100.0})
                    if done:
                        break
        except Exception,e: #Failure
            elapsedTime = time.time() - startTime
            if VERBOSE:
                print "exception",repr(e)
                traceback.print_exc()
            self.output += '\n' + repr(e)
            self.output += '\n' + traceback.format_exc(e)
            self.output += "\nProcessed {} bytes of {}".format(processedBytes, totalBytes)
            self.notifyProgress({'runState': RunState.FAIL_STATE, 'errorNumber': errorNumber, 'state': FAIL_WITH_ERROR_CODE_TEXT.format(errorNumber), 'output': self.output, 'elapsedTime':elapsedTime, 'chipId': self.serialNumber, 'returnValues':{'image':self.chpFileName}})
            return errorNumber 
        else: # Success
            elapsedTime = time.time() - startTime
            self.output += '\nTotal Time {}'.format(datetime.timedelta(seconds=elapsedTime))
            self.notifyProgress({'runState': RunState.PASS_STATE,'stage': stage, 'state': PASS_TEXT, 'output': self.output, 'elapsedTime':elapsedTime ,'chipId': self.serialNumber, 'returnValues':{'image':self.chpFileName}}) #eventually write manifest too
        finally:
            self.devicePort.releaseDevice()
        return SUCCESS

    def notifyProgress(self, progress):
        '''
        Send progress info to the shared queue
        :param progress: Progress object
        '''
        if self.progressQueue:
            progress['uid'] = self.deviceDescriptor.uid
            self.progressQueue.put(progress)

    def onFoundFel(self):
        '''
        This is called as a callback from the DevicePort when it finds a FEL device. When that happens, we read its serial number
        '''
        self.serialNumber = self.readSerialNumber()

    def readSerialNumber(self):
        '''
        Read serial number from the device. This will call Python FEL code. Then it will
        look up the device in the database, and if found, notifies of the record found.
        '''
        serialNumber = fel.getSerialNumber(self.devicePort)
        if serialNumber:
            # now, call the parent process asking it for an existing record in its databse
            self.connectionFromParent.send({'findChipId':serialNumber})
            result = self.connectionFromParent.recv()
            if result:
                dataDict = result['findChipId']
                if dataDict:
                    self.history = dataDict
                else:
                    self.history = {'attempts' : '0','chipId':serialNumber}
                    for i in xrange(8):
                        self.history['filler'+str(i)] = ''
                
                self.notifyProgress({'history':self.history})

                return serialNumber
            else:
                print "shouldn't happen"
        else:
            print 'ERROR failed to read serial from FEL.'
        return None

    def waitForStartTrigger(self):
        '''
        Wait until either the user clicks on a device row to start flashing, or if in auto-start mode,
        wait for the state directly
        '''
        if not AUTO_START_ON_DEVICE_DETECTION: #if parent sends messages to start... flashing below is allowed fail waiting for FEL
            while self.connectionFromParent.poll(): # clear out any pending stuff
                self.connectionFromParent.recv()
            self.connectionFromParent.recv() #now block until a message
            return True

        if self.devicePort.waitForState(FEL_VENDOR_ID, FEL_PRODUCT_ID, POLLING_NO_TIMEOUT): #This will wait forever
            return True
            
        return False
            
    def flashForever(self):
        '''
        Run the endless flashing loop for the process, handling errors correclty
        '''
        while True:
            try:
                if self.flash() == ERROR_DEVICE_NOT_FOUND: #201 errors. Need operator to click to clear them
                    self.connectionFromParent.send({'clickMe':self.deviceDescriptor.uid})
                    click = self.connectionFromParent.recv() #now block until a message
                    if VERBOSE:
                        print "Received {}".format(click)

                self.devicePort.waitForDisconnect()
                self.notifyProgress({'progress':0, 'runState': RunState.DISCONNECTED_STATE, 'state': DISCONNECTED_TEXT})
            except KeyboardInterrupt:
                return

    @staticmethod
    def manifest(chpFileName):
        return ChpFlash(None,None,None,{'chpFileName': chpFileName}).readManifest()
####################################################################################################
# Database stuff. This is a bit overkill how it's done 
    @staticmethod
    def statsTableName():
        '''
        Name of database table for flashing
        '''
        return "flash"

    CUSTOM_COLUMNS = [
                      ['image','TEXT',""]
                    ]

    @classmethod
    def statsTableColumns(cls):
        '''
        Get specific columns for flash (as opposed to the shared ones with hwtest)
        :param cls:
        '''
        return cls.CUSTOM_COLUMNS

    @staticmethod
    def getStatsQueries(where):
        '''
        Get the queries used to display in the UI. This is a WIP
        :param where: used to filter the query given table
        '''
        table = ChpFlash.statsTableName()
        return [
            "select count(*) as 'total', sum(1-result) as 'failed', sum(result) as 'passed' from {0} where {1}".format(table,where),
            "select avg(elapsedTime) as 'averageTime' from {0} where result=1 AND {1}".format(table,where),
            "select error as errors_key, count(error) as errors_val from {0} where error != 0 and {1} group by error order by error".format(table,where)
        ]

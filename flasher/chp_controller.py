'''
Created on Mar 15, 2017

@author: howie

This module is the core of multiprocess flashing. It maintains a list of child processes and manages the communication between it and
its children. This communication is in the form of clicks from the GUI to start flashing (or clear error), done via a Pipe, and
progress/state updates, which are managed by a Queue.
'''
from collections import OrderedDict
from sets import Set
from multiprocessing import Process, Pipe, Lock, Queue
import subprocess
from chp_flash import ChpFlash
from deviceDescriptor import DeviceDescriptor
from config import *
from pydispatch import dispatcher

PROGRESS_UPDATE_SIGNAL = "stateUpdate"
TRIGGER_SIGNAL = 'start'

def flash(progressQueue, connectionFromParent, lock, args):
    '''
    Body of the flashing subprocesses
    :param progressQueue: multiprocessing.Queue which will be sent progress updates
    :param connectionFromParent: From the Port that was created by the controller
    :param lock: Currently unused. Old flasher required a mutex, so thought it might be a useful placeholder for the future just in case
    :param args: Dictionary of args to pass along to the flasher. currently just the chp file name
    '''
    flasher = ChpFlash(progressQueue, connectionFromParent, lock, args)
    flasher.flashForever()

class ProcessDescriptor(object):
    '''
    Simple class to store values related to a subprocess
    '''
    __slots__ = ('deviceDescriptor', 'parent_conn', 'child_conn', 'process') #using slots prevents bugs where members are created by accident
    def __init__(self,  deviceDescriptor, parent_conn, child_conn):
        '''
        Constructor
        :param deviceDescriptor: Info about the physical port and udev rules
        :param parent_conn: Pipe connection on the parent side
        :param child_conn: Pipe connection on the child side
        '''
        self.deviceDescriptor = deviceDescriptor
        self.parent_conn = parent_conn
        self.child_conn = child_conn
        self.process = None
        
class ChpController(object):
    '''
    Class which manages a group of child processes, each one endlessly flashing the CHIP plugged into its associated port.
    '''
    __slots__ = ('fileInfo', 'progressQueue', 'chpFileName', 'lock', 'databaseLogger', 'awaitingClick', 'log', 'processDescriptors', 'deviceDescriptors', 'hubs', 'progressQueue') #using slots prevents bugs where members are created by accident
    def __init__( self, chpFileName, databaseLogger, log = None):
        '''
        Constructor. This class should be used as a singleton.
        :param chpFileName: Name of chp file to use for flashing
        :param databaseLogger: reference to the database - used to answer child's requests for info given a chipId
        :param log: unused for now
        '''
        self.chpFileName = chpFileName
        self.databaseLogger = databaseLogger
        self.log = log
        self.lock = Lock() #currently unused, but may need in future
        self.progressQueue = Queue()
        self.awaitingClick=Set() #These are devices in a 201 error state that are awaiting a click to clear the error
        self.processDescriptors = OrderedDict()
        self.deviceDescriptors, self.hubs = DeviceDescriptor.readRules(UDEV_RULES_FILE, SORT_DEVICES, SORT_HUBS) #read the UDEV info
        self.fileInfo = None #cached info about the .chp file

    def getFileInfo(self):
        '''
        Get the manifest info of a chp file as a dictionary
        '''
        if not self.fileInfo:
            self.fileInfo = {'file': self.chpFileName}
            manifest = ChpFlash.manifest(self.chpFileName)
            if manifest:
                self.fileInfo['size']=manifest['totalBytes']
                self.fileInfo['nand']=manifest['nandChip']['id']
                if self.fileInfo['nand'] == "Toshiba_512M_MLC": #fix for old improper manifests
                    self.fileInfo['nand'] = "Toshiba_512M_SLC"
            
        return self.fileInfo
            
    def createProcesses(self):
        '''
        Creates and starts a new flasher process. These processes flash in a loop, so they don't need to be restarted.
        '''

        for uid,dev in self.deviceDescriptors.iteritems():
            parent_conn, child_conn = Pipe() #if using button push, then will send start trigger through pipe
            args = {'chpFileName': self.chpFileName, 'deviceDescriptor': dev}
            processDescriptor = self.processDescriptors[uid] = ProcessDescriptor(dev, parent_conn, child_conn)
            processDescriptor.process = Process(target = flash, args = (self.progressQueue, child_conn, self.lock, args))
            processDescriptor.process.start()
    
    def checkForChanges(self):
        '''
        Called from main loop - checks the progress queue and pipe for communication from children
        '''
        self.processProgressQueue()
        self.checkForCallsFromChild();
        
    def processProgressQueue(self):
        '''
        Get any pending progress updates from the processes
        '''
        while not self.progressQueue.empty():
            progress = self.progressQueue.get()
            dispatcher.send(signal = PROGRESS_UPDATE_SIGNAL, info = progress, sender=self)
       
    def checkForCallsFromChild(self):
        '''
        Go through each child and see if it sent a message. If so, respond by sending something back. Essentially, a synchronous RPC
        '''
        for proc in self.processDescriptors.itervalues():
            while proc.parent_conn.poll(): #check for requests from child
                call = proc.parent_conn.recv() #read what child sent
                #below is a little clumsy, but ok for now since we only have 2 calls
                findChipId = call.get('findChipId')
                if findChipId:
                    data = self.databaseLogger.find(findChipId) #lookup info in the database
                    proc.parent_conn.send({'findChipId':data})
                clickMe = call.get('clickMe') #for 201 errors awaiting a clearing click
                if clickMe:
                    self.awaitingClick.add(int(clickMe)) #add to set of rows that await a click
    
    def joinAll(self):
        '''
        Join all subprocesses, such as when exiting
        '''
        for processDescriptor in self.processDescriptors.itervalues():
            processDescriptor.process.join()
        
    def getStatsQueries(self,suiteName,where=None):
        '''
        Called in response to user request, get the query to read stats
        :param suiteName: Not used anymore
        :param where: Filter expression
        '''
        return ChpFlash.getStatsQueries(where)

    def powerOff(self):
        '''
        Will poweroff the computer
        '''
        try:
            subprocess.Popen( ["systemctl","poweroff"])
        except Exception,e:
            print e    
            
    def onTriggerDevice(self,uid):
        '''
        In response to a user click, send the click to the appropriate subprocesses. If that subprocesses is
        explicitly awaiting a click to clear out an error message, handle it accordingly.
        :param uid: The id of the device/process (1-n)
        '''
        if CLICK_TRIGGERS_ALL:
            procs = self.processDescriptors #going to send event to all of them
        else:
            procs = {uid: self.processDescriptors.get(uid)}
        for procUid,processDescriptor in procs.iteritems():
            pid = int(procUid)
            if processDescriptor.child_conn:
                if pid in self.awaitingClick: #if explicitly clicked on an item that's awaiting input
                    if uid == procUid or not CLICK_ONLY_APPLIES_TO_SINGLE_201:
                        self.awaitingClick.remove(pid)
                    else:
                        continue #don't send click unless explicitly clicked on
                
                processDescriptor.parent_conn.send('start')


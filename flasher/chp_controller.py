'''
Created on Mar 15, 2017

@author: howie
'''
from collections import OrderedDict
from sets import Set
from multiprocessing import Process, Pipe, Lock, Queue
from chp_flash import ChpFlash
from deviceDescriptor import DeviceDescriptor
from config import *
from pprint import pformat
from pydispatch import dispatcher

PROGRESS_UPDATE_SIGNAL = "stateUpdate"

def flash(progressQueue, connectionFromParent, lock, args):
    flasher = ChpFlash(progressQueue, connectionFromParent, lock, args)
    flasher.flashForever()

class ProcessDescriptor(object):
    __slots__ = ('deviceDescriptor', 'parent_conn', 'child_conn', 'process') #using slots prevents bugs where members are created by accident
    def __init__(self,  deviceDescriptor, parent_conn, child_conn):
        self.deviceDescriptor = deviceDescriptor
        self.parent_conn = parent_conn
        self.child_conn = child_conn
        
class ChpController(object):
    __slots__ = ('fileInfo', 'progressQueue', 'chpFileName', 'lock', 'databaseLogger', 'awaitingClick', 'log', 'processDescriptors', 'deviceDescriptors', 'hubs', 'progressQueue') #using slots prevents bugs where members are created by accident
    def __init__( self, chpFileName, databaseLogger, log = None):

        self.chpFileName = chpFileName
        self.databaseLogger = databaseLogger
        self.log = log
        self.lock = Lock() #currently unused, but may need in future
        self.progressQueue = Queue()
        self.awaitingClick=Set()
        self.processDescriptors = OrderedDict()
        self.deviceDescriptors, self.hubs = DeviceDescriptor.readRules(UDEV_RULES_FILE, SORT_DEVICES, SORT_HUBS)
        self.fileInfo = None
        
    def getFileInfo(self):
        if not self.fileInfo:
            self.fileInfo = "File: " + self.chpFileName
            manifest = ChpFlash(None,None,None,{'chpFileName': self.chpFileName}).readManifest()
            self.fileInfo += '\nManifest: ' + pformat(manifest,width=1)
            
        return self.fileInfo
            
    def createProcesses(self):
        for uid,dev in self.deviceDescriptors.iteritems():
            parent_conn, child_conn = Pipe() #if using button push, then will send start trigger through pipe
            args = {'chpFileName': self.chpFileName, 'deviceDescriptor': dev}
            processDescriptor = self.processDescriptors[uid] = ProcessDescriptor(dev, parent_conn, child_conn)
            processDescriptor.process = Process(target = flash, args = (self.progressQueue, child_conn, self.lock, args))
            processDescriptor.process.start()
    
    def checkForChanges(self):
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
        for proc in self.processDescriptors.itervalues():
            while proc.parent_conn.poll(): #check for requests from child
                call = proc.parent_conn.recv()
                findChipId = call.get('findChipId')
                if findChipId:
                    data = self.databaseLogger.find(findChipId)
                    proc.parent_conn.send({'findChipId':data})
                clickMe = call.get('clickMe')
                if clickMe:
                    self.awaitingClick.add(int(clickMe))
    
    def joinAll(self):
        for processDescriptor in self.processDescriptors.itervalues():
            processDescriptor.process.join()
        
    def getStatsQueries(self,suiteName,where=None):
        return ChpFlash.getStatsQueries(where)
    
    def onTriggerDevice(self,uid):
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


'''
Created on Mar 15, 2017

@author: howie
'''
from collections import OrderedDict
from sets import Set
from multiprocessing import Process, Queue, Pipe, Lock
from chp_flash import ChpFlash
from deviceDescriptor import DeviceDescriptor
from config import *
import time
from pprint import pprint, pformat

def flash(progressQueue, connectionFromParent, lock, args):
    flasher = ChpFlash(progressQueue, connectionFromParent, lock, args)
#     manifest = flasher.flash(True)
    flasher.flashForever()

class ProcessDescriptor(object):
    __slots__ = ('deviceDescriptor', 'parent_conn', 'child_conn', 'process') #using slots prevents bugs where members are created by accident
    def __init__(self,  deviceDescriptor, parent_conn, child_conn):
        self.deviceDescriptor = deviceDescriptor
        self.parent_conn = parent_conn
        self.child_conn = child_conn
        
class ChpController(object):
    __slots__ = ('fileInfo', 'progressQueue', 'chpFileName', 'lock', 'databaseLogger', 'awaitingClick', 'log', 'processDescriptors', 'deviceDescriptors', 'hubs', 'progressQueue') #using slots prevents bugs where members are created by accident
    def __init__( self, progressQueue, chpFileName, databaseLogger, log = None):
        self.progressQueue = progressQueue
        self.chpFileName = chpFileName
        self.databaseLogger = databaseLogger
        self.log = log
        self.lock = Lock()
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


def main():
    progressQueue = Queue() #multiprocessing version of queue
#     chpFileName = '/home/howie/Downloads/stable-chip-pro-blinkenlights-b1-Toshiba_512M_SLC.chp'
    chpFileName = '/home/howie/Downloads/stable-gui-b149-nl-Hynix_8G_MLC.chp'

    chpController = ChpController(progressQueue, chpFileName)
    chpController.createProcesses()
    i = 0
    try:
        while True:
            i = i +1
            while not progressQueue.empty():
                progress = progressQueue.get()
                print progress
            time.sleep(.1)
            if i % 50 == 0:
                for uid, processDescriptor in chpController.processDescriptors.iteritems():
                    if processDescriptor.child_conn:
                        processDescriptor.parent_conn.send("start")
    except KeyboardInterrupt:
        chpController.joinAll() # wait for all of them to exit. The keyboard interrupt is sent to them automatically by Python

     
#         thread.join()
#------------------------------------------------------------------
if __name__ == "__main__":
#------------------------------------------------------------------
    exit( main() )
    

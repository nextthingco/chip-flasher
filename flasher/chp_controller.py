'''
Created on Mar 15, 2017

@author: howie
'''
from collections import OrderedDict
from multiprocessing import Process, Queue, Pipe
from chp_flash import ChpFlash
from deviceDescriptor import DeviceDescriptor
from config import *
import time
from pprint import pprint

def flash(progressQueue, connectionFromParent, args):
    flasher = ChpFlash(progressQueue, connectionFromParent, args)
#     manifest = flasher.flash(True)
    flasher.flashForever()

class ProcessDescriptor(object):
    __slots__ = ('deviceDescriptor', 'parent_conn', 'child_conn', 'process') #using slots prevents bugs where members are created by accident
    def __init__(self,  deviceDescriptor, parent_conn, child_conn):
        self.deviceDescriptor = deviceDescriptor
        self.parent_conn = parent_conn
        self.child_conn = child_conn
        
class ChpController(object):
    __slots__ = ('fileInfo', 'progressQueue', 'chpFileName', 'log', 'processDescriptors', 'deviceDescriptors', 'hubs', 'progressQueue') #using slots prevents bugs where members are created by accident
    def __init__( self, progressQueue, chpFileName, log = None):
        self.progressQueue = progressQueue
        self.chpFileName = chpFileName
        self.log = log
        self.processDescriptors = OrderedDict()
        self.deviceDescriptors, self.hubs = DeviceDescriptor.readRules(UDEV_RULES_FILE, SORT_DEVICES, SORT_HUBS)
        self.fileInfo = None
        
    def getFileInfo(self):
        return self.chpFileName
            
    def createProcesses(self):
        for uid,dev in self.deviceDescriptors.iteritems():
            if AUTO_START_ON_DEVICE_DETECTION:
                parent_conn = child_conn = None
            else:
                parent_conn, child_conn = Pipe() #if using button push, then will send start trigger through pipe
            args = {'chpFileName': self.chpFileName, 'deviceDescriptor': dev}
            processDescriptor = self.processDescriptors[uid] = ProcessDescriptor(dev, parent_conn, child_conn)
            processDescriptor.process = Process(target = flash, args = (self.progressQueue, child_conn, args))
            processDescriptor.process.start()
    
    def joinAll(self):
        for processDescriptor in self.processDescriptors.itervalues():
            processDescriptor.process.join()  

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
    

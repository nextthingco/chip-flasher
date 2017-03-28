'''
Created on Mar 15, 2017

@author: howie

Module to parse udev rules which are used to both identify usb devices, and format the flasher GUI
'''
import re
from collections import OrderedDict
UDEV_REGEX = re.compile(ur'.*KERNELS.*\"(.*)\".*ATTRS\{idVendor}.*\"(.*)\".*ATTRS\{idProduct\}.*\"(.*)\".*GROUP.*\".*\".*MODE.*\".*\".*SYMLINK.*\"(.*)\"')
SYMLINK_REGEX = re.compile(r".*chip-(.*)-(.*)-(.*)")
                           
NAME_FROM_UDEV_REGEX = re.compile(r".*chip-(.*)-usb")

class DeviceDescriptor:
    '''
    Class which holds the udev values for a single port
    '''
    DEVICE_NULL = -1 #no state yet
    DEVICE_DISCONNECTED = 0
    DEVICE_FEL = 1
    DEVICE_FASTBOOT = 2
    DEVICE_SERIAL = 3
    DEVICE_ETHERNET = 5
    DEVICE_WAITING_FOR_FASTBOOT = 4
    def __init__(self, uid, hub, kernel, vendor, product, _type): #store off all values for convenience
        '''
        Constructor. Values come from udev rules
        :param uid:
        :param hub:
        :param kernel:
        :param vendor:
        :param product:
        :param _type:
        '''
        self.uid = uid
        self.hub = hub
        self.kernel = kernel
        self.vendor = vendor
        self.product = product
        self.type = _type
        self.fel = None
        self.fastboot = None
        self.serial = None
        self.ethernet = None
    
    @staticmethod
    def readRules(rulesFilePath, sortDevices = True, sortHubs = True):
        '''
        Parse a udev file and construct a map of descriptors which map fel, fastboot, and serial to a physical port
        The symlink should have format: chip_[id]_[hub]_[fel | fastboot | serial]
        See the REGEXs at the top of this file for the expected format.
        There are other, maybe better approaches to this, for example, running udevadm info -e
        and parsing that result for the appropriate devices
        
        It will construct an ordered dictionary of devices and hubs in the order encountered in the rules file.
        If sortDevices is true, then the dictionary will be sorted by id, numerically. If it is not numeric, it will not work
        If sort hubs is true, then it will sort the hubs alphabetically
        :param rulesFilePath:
        '''
        descriptorMap = OrderedDict() #preserve order from udev file
        hubs = []
        with open(rulesFilePath, 'r') as rulesFile:
            for line in rulesFile:
                match = UDEV_REGEX.match(line)
                if match:
                    kernel = match.group(1)
                    vendor = match.group(2)
                    product = match.group(3)
                    symlink = match.group(4)
                    
                    symlinkMatch = SYMLINK_REGEX.match(symlink) #parse out the uid, hub and type from the symlink
                    uid = symlinkMatch.group(1)
                    hub = symlinkMatch.group(2)
                    _type = symlinkMatch.group(3)
                    
                    if uid in descriptorMap:
                        descriptor = descriptorMap[uid]
                    else:
                        descriptor = DeviceDescriptor(uid,hub,kernel,vendor,product,_type)
                        descriptorMap[uid] = descriptor
                    device = '/dev/' + symlink  
                    
                    # currently using vid_pid to determine type. The "type" field could be used instead  
                    if vendor == '1f3a' and product == 'efe8':
                        descriptor.fel = device
                    elif vendor == '1f3a' and product == '1010':
                        descriptor.fastboot = device
                    elif vendor == "0525" and product == 'a4aa':
                        descriptor.serial = device
                    elif vendor == "0525" and product == 'a4a7':
                        descriptor.serial = device
                    elif vendor == "2dfe" and product == 'beef':
                        descriptor.ethernet = device
                    
                    if not hub in hubs: #add to hub list
                        hubs.append(hub)
        
        if sortDevices:
            descriptorMap = OrderedDict(sorted(descriptorMap.iteritems(), key=lambda x: int(x[1].uid)))
        if sortHubs:
            hubs.sort
                
        return descriptorMap, hubs
    
        
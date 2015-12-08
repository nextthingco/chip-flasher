import re
from collections import OrderedDict

UDEV_REGEX = re.compile(ur'.*KERNELS.*\"(.*)\".*ATTR\{idVendor}.*\"(.*)\".*ATTRS\{idProduct\}.*\"(.*)\".*SYMLINK.*\"(.*)\"')
SYMLINK_REGEX = re.compile(r".*chip-(.*)-(.*)-(.*)")
                           
NAME_FROM_UDEV_REGEX = re.compile(r".*chip-(.*)-usb")

class DeviceDescriptor:
    def __init__(self, uid, hub, kernel, vendor, product, type): #store off all values for convenience
        self.uid = uid
        self.hub = hub
        self.kernel = kernel
        self.vendor = vendor
        self.product = product
        self.type = type
        self.fel = None
        self.fastboot = None
        self.serial = None
        self.serialConnection = None #used when accessing device as a serial gadget
        self.widgetInfo = {} #widgets in GUI
       
    @staticmethod
    def makeDummy():
        return DeviceDescriptor('0','0','0','0','0','0-0-0')
    
    def setWidgetColor(self,color):
        for widget in self.widgetInfo.itervalues():
            widget.color = color
    
    
    def textForLog(self):
        return "Port: " + self.uid + "\n"
    
    @staticmethod
    def readRules(rulesFilePath):
        '''
        Parse a udev file and construct a map of descriptors which map fel, fastboot, and serial to a physical port
        There are other, maybe better approaches to this, for example, running udevadm info -e
        and parsing that result for the appropriate devices
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
                    type = symlinkMatch.group(3)
                    
                    if uid in descriptorMap:
                        descriptor = descriptorMap[uid]
                    else:
                        descriptor = DeviceDescriptor(uid,hub,kernel,vendor,product,type)
                        descriptorMap[uid] = descriptor
                    device = '/dev/' + symlink  
                    
                    # currently using vid_pid to determine type. The "type" field could be used instead  
                    if vendor == '1f3a' and product == 'efe8':
                        descriptor.fel = device
                    elif vendor == '18d1' and product == '1010':
                        descriptor.fastboot = device
                    elif vendor == "0525" and product == 'a4a7':
                        descriptor.serial = device
                    
                    if not hub in hubs: #add to hub list
                        hubs.append(hub)
                        
        return descriptorMap, hubs
    
        
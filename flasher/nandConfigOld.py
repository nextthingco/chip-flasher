#!/usr/bin/env python
from serialconnection import SerialConnection
from unittest import TestCase, TextTestRunner, TestLoader
from observable_test import *
from commandRunner import CommandRunner
import os
import re
import time
import threading
from config import *
from deviceDescriptor import DeviceDescriptor
from ui_strings import *
from secrets import *

dummy = DeviceDescriptor.makeDummy()

WIFI_DISCONNECT = "nmcli device disconnect wlan0"
WIFI_CONNECT_FORMAT="nmcli device wifi connect '{0}' password '{1}' ifname wlan0"

hostnameCounter = HOSTNAME_COUNTER

class NandConfigOld(TestCase):
    ser = None

    def __init__(self, *args, **kwargs):
        super(NandConfigOld, self).__init__(*args, **kwargs)       
        self.logMutex = threading.Lock()
        
    def logHostAndSerial(self, hostname, serial):
        with self.logMutex:
            with open(HOSTNAME_SERIAL_FILE,"a") as file:
                file.write("{0}\t{1}\n".format(hostname,serial))

    def setUp(self):
        self.progressObservers = []
        try:
            self.deviceDescriptor = self.attributes['deviceDescriptor']
        except:  # run from regular unit test
            global dummy
            self.deviceDescriptor = dummy  # a dummy object
            self.deviceDescriptor.serial = "/dev/chip-8-2-serial"


    def tearDown(self):
        pass
#         print "killing serial connection"
#         self.ser.close()
#         self.ser = None
        
#     def setUp(self):
#         try:
#             print "setup------------------------"
# #             if False:
# #                 if( not os.path.exists("/etc/udev/rules.d/uart.rules") ):
# #                     # Create udev rule for our UART serial cable if it doesn't already exist.
# #                     # This code will probably need to change once we're testing more than one CHIP at once.
# #                     file = open("/etc/udev/rules.d/uart.rules", "w")
# #                     file.write("ACTION==\"add\", ATTRS{idVendor}==\"067b\", ATTRS{idProduct}==\"2303\", SYMLINK+=\"uart\"")
# #                     file.close()
# #                     os.system("sudo udevadm trigger")
# #                     print( "UART udev rule created! You may need to unplug and replug the USB device and restart.")
# #                     print( "Please try again.")
# #     
# #                 self.ser = SerialConnection("root","chip","/dev/uart")
#             self.ser = SerialConnection("root","chip","/dev/chip_usb")
# 
#         except Exception, e:
#             raise Exception( "Failed to connect to CHIP" )
# 
#     def tearDown(self):
#         TestCase.tearDown(self)
#         self.ser.close()


    def findSerialDevice(self):
        return os.path.exists(self.deviceDescriptor.serial)

    @label(UI_WAITING_FOR_DEVICE)
    @progress(FIND_SERIAL_TIME)
    @errorNumber(301)
    @failMessage(FAIL_301_TEXT)
    def test_000_serial(self):
        self.deviceDescriptor.serialNumber = "-"
        self.deviceDescriptor.deviceId = "-"
        for attempt in range(1, FIND_SERIAL_TIME):
            if self.findSerialDevice():
                return True
            time.sleep(1)
        raise Exception(
            "No Serial device found: " + self.deviceDescriptor.serial)

        
    @label("Logging in")
    @progress(10)
    @timeout(15)
    def test_001_initial(self):
        print "logging in"
        ser = self.deviceDescriptor.serialConnection = SerialConnection("root","chip",self.deviceDescriptor.serial)
        ser.connect()
        time.sleep(5);
        print "sending hostname"
        #print( "Waiting for CHIP to boot...")


    @label("Connect to wifi")
    @progress(5)
    @timeout(15)
    def test_003_wifi(self):
        ser = self.deviceDescriptor.serialConnection
        ser.send(WIFI_DISCONNECT) #disconnect if alredy connected. Allows reflashing with a network already up
        connectionString = WIFI_CONNECT_FORMAT.format(TEST_FARM_SSID, TEST_FARM_PASSWORD)
        conResult = ser.send(connectionString);
        if  "ailed" in conResult:
            raise Exception("Could not connect")
        print conResult
        


    @label("apt-get update")
    @progress(60)
    @timeout(200)
    def test_004_update(self):
        ser = self.deviceDescriptor.serialConnection
  
        ser.send("apt-get update")

    @label("install packages")
    @progress(60)
    @timeout(60)
    def test_005_git(self):
        ser = self.deviceDescriptor.serialConnection
        ser.send("apt-get --yes --force-yes install git build-essential bonnie++ python-serial")
        
    @label("clone repo")
    @progress(10)
    @timeout(10)
    def test_006_repo(self):
        ser = self.deviceDescriptor.serialConnection
        ser.send("rm -rf " + NAND_TEST_PROJECT) #in case of reflash, remove old one
        cmd = NAND_TEST_REPO.format(NAND_REPO_USER,NAND_REPO_PASSWORD)
        ser.send(cmd)
        
    @label("install tests")
    @progress(10)
    @timeout(10)
    def test_007_test(self):
        
        ser = self.deviceDescriptor.serialConnection
        ser.send("cd CHIP-nandTests");
        
        global hostnameCounter
        self.deviceDescriptor.testGroup = hostnameCounter % len(NAND_TESTS) #chips will be assigned a test to run

        testName = NAND_TESTS[self.deviceDescriptor.testGroup]
        if NAND_TEST_FORCE:
            testName = NAND_TEST_FORCE

        test = NAND_TEST_FORMAT.format(testName)
        
        print "!!TEST NAME IS: " + testName + "    group " + str(self.deviceDescriptor.testGroup)
        ser.send(test)
        
        
    @label("change hostname")
    @progress(6)
    @timeout(15)
    def test_008_hostname(self):
        #if all has gone well, set the hostname and write it and serial to a file
        ser = self.deviceDescriptor.serialConnection
        deviceId = self.deviceDescriptor.deviceId = ser.send("hostname")
        
        if deviceId == None:
            raise Exception("no deviceId")
                            
        serialNumber = self.deviceDescriptor.serialNumber = ser.send(SERIAL_NUMBER_COMMAND)
        
        if serialNumber == None:
            raise Exception("no serial")
            
        print "Serial number " + serialNumber
#         print "Hostname is: " + deviceId + " serial is " + serialNumber
#         if re.search(r'.*(chip|TN_\d\d\d).*',deviceId):
#             print( "CHIP FOUND! Running tests...")
#         else:
#             print deviceId
#             raise Exception( "Hostname not found." )

        
        global hostnameCounter
        newName = HOSTNAME_FORMAT.format(hostnameCounter);
        hostnameCounter += 1;
        deviceId = self.deviceDescriptor.deviceId
        
        self.logHostAndSerial(newName,self.deviceDescriptor.serialNumber )
        
#         print "Current host name is " + deviceId
        cmd1 = 'sed -i "s/{0}/{1}/g" /etc/hostname'.format(deviceId,newName)
        cmd2 = 'sed -i "s/{0}/{1}/g" /etc/hosts'.format(deviceId,newName)
        self.deviceDescriptor.deviceId = newName

        ser.send(cmd1)
        ser.send(cmd2)        


    @label("add syslog server")
    @progress(10)
    @timeout(10)
    def test_009_repo(self):
        ser = self.deviceDescriptor.serialConnection
        cmd = "echo '*.*   @@seshat.local:514' | tee -a /etc/rsyslog.conf"
        ser.send(cmd);
        
    @label("Disconnecting")
    @progress(10)
    @timeout(10)
    def test_010_disconnect(self):
        ser = self.deviceDescriptor.serialConnection
        ser.close()
        self.deviceDescriptor.serialConnection = None


    
def main():
    tl = TestLoader()
    suite = tl.loadTestsFromTestCase(FactoryHardwareTest)
    result = TextTestRunner(verbosity=2, failfast=True).run(suite) # This runs the whole suite of tests. For now, using TextTestRunner
    print result

#------------------------------------------------------------------
if __name__ == "__main__":
#------------------------------------------------------------------
  exit( main() )

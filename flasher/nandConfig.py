#!/usr/bin/env python
from serialconnection import SerialConnection
from unittest import TestCase, TextTestRunner, TestLoader
from observable_test import *
from commandRunner import CommandRunner
import os
import re
import time
from config import *
from deviceDescriptor import DeviceDescriptor
from ui_strings import *
from secrets import *

dummy = DeviceDescriptor.makeDummy()

WIFI_CONNECT_FORMAT="nmcli device wifi connect '{0}' password '{1}' ifname wlan0"

class NandConfig(TestCase):
    ser = None
    hostnameCounter = HOSTNAME_COUNTER

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
        deviceId = self.deviceDescriptor.deviceId = ser.send("hostname")
        print "Hostname is: " + deviceId
        if re.search(r'.*chip.*',deviceId):
            print( "CHIP FOUND! Running tests...")
        else:
            print deviceId
            raise Exception( "Hostname not found." )

    @label("change hostname")
    @progress(6)
    @timeout(15)
    def test_002_hostname(self):
        ser = self.deviceDescriptor.serialConnection

        self.deviceDescriptor.testGroup = self.hostnameCounter % len(NAND_TESTS) #chips will be assigned a test to run
        newName = HOSTNAME_FORMAT.format(self.hostnameCounter);
        self.hostnameCounter += 1;
        deviceId = self.deviceDescriptor.deviceId
        print "CUrrent host name is " + deviceId
        cmd1 = 'sed -i "s/{0}/{1}/g" /etc/hostname'.format(deviceId,newName)
        cmd2 = 'sed -i "s/{0}/{1}/g" /etc/hosts'.format(deviceId,newName)
        self.deviceDescriptor.deviceId = newName

        ser.send(cmd1)
        ser.send(cmd2)        

    @label("Connect to wifi")
    @progress(5)
    @timeout(15)
    def test_003_wifi(self):
        ser = self.deviceDescriptor.serialConnection
        connectionString = WIFI_CONNECT_FORMAT.format(TEST_FARM_SSID, TEST_FARM_PASSWORD)
        conResult = ser.send(connectionString);
        print conResult
        


    @label("apt-get update")
    @progress(60)
    @timeout(200)
    def test_004_update(self):
        ser = self.deviceDescriptor.serialConnection
  
        ser.send("apt-get update")

    @label("install git")
    @progress(60)
    @timeout(60)
    def test_005_git(self):
        ser = self.deviceDescriptor.serialConnection
        ser.send("apt-get -y install git")
        
    @label("clone repo")
    @progress(10)
    @timeout(10)
    def test_006_repo(self):
        ser = self.deviceDescriptor.serialConnection
        cmd = NAND_TEST_REPO.format(NAND_REPO_USER,NAND_REPO_PASSWORD)
        ser.send(cmd)
        
    @label("install tests")
    @progress(10)
    @timeout(10)
    def test_007_repo(self):
        ser = self.deviceDescriptor.serialConnection
        ser.send("cd CHIP-nandTests");
        testName = NAND_TESTS[self.deviceDescriptor.testGroup]
        if NAND_TEST_FORCE:
            testName = NAND_TEST_FORCE

        test = NAND_TEST_FORMAT.format(testName)
        ser.send(test)
        
        
    @label("add syslog server")
    @progress(10)
    @timeout(10)
    def test_008_repo(self):
        ser = self.deviceDescriptor.serialConnection
        cmd = "echo '*.*   @@seshat.local:514' | tee -a /etc/rsyslog.conf"
        ser.send(cmd);
        
    @label("Disconnecting")
    @progress(10)
    @timeout(10)
    def test_009_disconnect(self):
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

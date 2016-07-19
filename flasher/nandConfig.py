#!/usr/bin/env python
from serialconnection import SerialConnection
from unittest import TestCase, TextTestRunner, TestLoader
from observable_test import *
from commandRunner import CommandRunner
import os
import re
import time
import threading
import string
from config import *
from deviceDescriptor import DeviceDescriptor
from ui_strings import *
from secrets import *

dummy = DeviceDescriptor.makeDummy()

WIFI_DISCONNECT = "nmcli device disconnect wlan0"
WIFI_CONNECT_FORMAT="nmcli device wifi connect '{0}' password '{1}' ifname wlan0"

hostnameCounter = HOSTNAME_COUNTER

class NandConfig(TestCase):
    ser = None

    def __init__(self, *args, **kwargs):
        super(NandConfig, self).__init__(*args, **kwargs)       
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

        
    def copyFileToSerial2(self, source, dest):
        ser = self.deviceDescriptor.serialConnection
        self.send(ser,"rm -f " + dest) #clear out old one so we can re-execute if need be
        ser.send("cat <<-EOF >> " +dest, blind=True)
        time.sleep(.4)
        with open(source) as f:
            for line in f:
                line = line.rstrip() #get rid of newline
                line = string.replace(line,"'","'\''")
                line = string.replace(line,"%NAND_REPO_USER%",NAND_REPO_USER)
                line = string.replace(line,"%NAND_REPO_PASSWORD%",NAND_REPO_PASSWORD)
                
#                 print line
                ser.send(line,blind=True)
                ser.flush()
                time.sleep(.4)
        ser.send("EOF")
        time.sleep(.4)
        ser.flush()
                
    def copyFileToSerial(self, source, dest):
        ser = self.deviceDescriptor.serialConnection
        self.send(ser,"rm -f " + dest) #clear out old one so we can re-execute if need be
        with open(source) as f:
            for line in f:
                line = line.rstrip() #get rid of newline
                line = line.strip();
                line = string.replace(line,"'","\'")
                line = string.replace(line,"%NAND_REPO_USER%",NAND_REPO_USER)
                line = string.replace(line,"%NAND_REPO_PASSWORD%",NAND_REPO_PASSWORD)
                
                print line
                ser.send("echo '{0}' >> {1}".format(line,dest),blind=False)
                ser.flush()
                time.sleep(.4)

    @label("Logging in")
    @progress(10)
    @timeout(15)
    def test_001_initial(self):
        print "logging in"
        ser = self.deviceDescriptor.serialConnection = SerialConnection("root","chip",self.deviceDescriptor.serial)
        ser.connect()
        time.sleep(3);
        #print( "Waiting for CHIP to boot...")


        
    @label("Copy Scripts")
    @progress(5)
    @timeout(15)
    def test_002_copyScripts(self):
        ser = self.deviceDescriptor.serialConnection        
        self.copyFileToSerial("bootstrap.sh", "/usr/sbin/bootstrap.sh")
        ser.flush()
        time.sleep(2)
        self.send(ser,"chmod +x /usr/sbin/bootstrap.sh")
        
        ser.flush()
    
        self.copyFileToSerial("bootstrap.service", "/etc/systemd/system/bootstrap.service")
        
        self.copyFileToSerial("testStress.service", "/etc/systemd/system/testStress.service")

        self.send(ser,"systemctl enable bootstrap.service")
        ser.flush()


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


    @label("change hostname")
    @progress(6)
    @timeout(15)
    def test_004_hostname(self):
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

        self.send(ser,cmd1)
        self.send(ser,cmd2)
        ser.flush()


    @label("add syslog server")
    @progress(10)
    @timeout(10)
    def test_009_repo(self):
        ser = self.deviceDescriptor.serialConnection
        cmd = "echo '*.*   @@seshat.local:514' | tee -a /etc/rsyslog.conf"
        self.send(ser,cmd);
        ser.flush()
        
    @label("Disconnecting")
    @progress(10)
    @timeout(10)
    def test_010_disconnect(self):
        ser = self.deviceDescriptor.serialConnection
        ser.flush()
        ser.close()
        self.deviceDescriptor.serialConnection = None


    def send(self,ser,cmd):
        ser.send(cmd)
        time.sleep(.4)
    
def main():
    tl = TestLoader()
    suite = tl.loadTestsFromTestCase(FactoryHardwareTest)
    result = TextTestRunner(verbosity=2, failfast=True).run(suite) # This runs the whole suite of tests. For now, using TextTestRunner
    print result

#------------------------------------------------------------------
if __name__ == "__main__":
#------------------------------------------------------------------
  exit( main() )

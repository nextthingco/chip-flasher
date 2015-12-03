#!/usr/bin/env python
from serialconnection import SerialConnection
from unittest import TestCase, TextTestRunner, TestLoader
from observable_test import *
from commandRunner import CommandRunner
import os
import re
import time

class FactoryHardwareTest(TestCase):
    ser = None

    @classmethod
    def setUpClass(cls):
        print "making serial connection"
        cls.ser = SerialConnection("root","chip","/dev/chip_usb")
        cls.ser.connect()

    @classmethod
    def tearDownClass(cls):
        print "killing serial connection"
        cls.ser.close()
        cls.ser = None
        
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
        
    @label("Waiting for boot...\n chinese")
    @progress(30)
    @timeout(90)
    @promptBefore("Click to begin\n in Chinese")

    def test_001_initial(self):
        #print( "Waiting for CHIP to boot...")
        hostname = self.ser.send("hostname",timeout=90)
        if re.search(r'.*chip.*',hostname):
            print( "CHIP FOUND! Running tests...")
        else:
            print hostname
            raise Exception( "Hostname not found." )

    @label("Activate WLAN...\n chinese")
    @progress(60)
    @timeout(5)

    def test_002_wlan(self):
        for x in range(3):
            print( "Activating WLAN" + str(x) + "...")
            self.ser.send("sudo ip link set wlan0 up")
            code = self.ser.send("echo $?")
            print "code is :" + str(code)
            if code == "0":
                print( "PASSED" )
            else:
                print "code is: " + str(code)
                raise Exception( "WLAN " + str(x) + " failed." )

    @label("WLAN enum...\n chinese")
    @progress(60)
    @timeout(5)

    def test_003_wlanEnum(self):
        print( "Testing WLAN enum..."),
        wlan = self.ser.send("iw dev|grep -v addr |grep -v ssid")
        wlanCompare = self.ser.send("cat /usr/lib/hwtest/wifi_ref0.txt")
        wlan = ''.join(wlan.split())
        wlanCompare = ''.join(wlanCompare.split())
        if re.search(r'.*' + wlanCompare + '.*',wlan):
            print( "PASSED")
        else:
            raise Exception( "WLAN enum failed." )

    @label("I2C...\n chinese")
    @progress(60)
    @timeout(5)

    def test_004_i2c(self):
        for x in range(2):
            print( "Testing I2C" + str(x) + "..."),
            i2c = self.ser.send("i2cdetect -y " + str(x))
            bPassed = False
            if x == 0 and re.search(r'.*UU.*',i2c):
                print( "pass1")
                bPassed = True
            elif x == 1 and re.search(r'.* 50 .*',i2c):
                bPassed = True
                print( "pass2")
            elif x == 2 and re.search(r'.*UU.*',i2c) and re.search(r'.* 50 .*',i2c):
                bPassed = True 
                print( "pass3")

            if bPassed:
                print( "PASSED" )
            else:
                raise Exception( "I2C failed." )

    @label("Hardware list...\n chinese")
    @progress(60)
    @timeout(2)

    def test_005_hardwareListTest(self):
        print( "Testing hardware list...")
        hardwareList = self.ser.send("lshw -disable usb -disable scsi |grep -v size|grep -v self.serial| grep -v physical |grep -v configuration")
        compareList = self.ser.send("cat /usr/lib/hwtest/lshw_ref.txt")
        compareList = hardwareList.replace( "network:1 DISABLED", "network:1") #Hack. Sometimes network1 is disabled, which isn't a failure.
        hardwareList = compareList.replace( "network:1 DISABLED", "network:1")
        hardwareList = ''.join(hardwareList.split())
        compareList = ''.join(compareList.split())
        
        if( compareList == hardwareList ):
            print( "PASSED")
        else:
            raise Exception( "Hardware list failed." )

    @label("AXP209...\n chinese")
    @progress(60)
    @timeout(5)

    def test_006_axp(self):
        print( "Testing AXP209..."),
        axp = self.ser.send("dmesg |grep axp |sed -e 's/\[.*\]//'")
        print "axp"
        print axp
        axpCompare = self.ser.send("cat /usr/lib/hwtest/axp_ref.txt")
        print "axpcompare"
        print axpCompare
#hk         time.sleep(0.5)
        if re.search(r'.*' + axpCompare + '.*',axp):
            print( "PASSED")
        else:
            raise Exception( "AXP209 failed." )

    @label("GPIO Expander...\n chinese")
    @progress(60)
    @timeout(5)

    def test_007_gpioExpander(self):
        print( "Testing GPIO expander..."),
        gpio = self.ser.send("cat /sys/bus/i2c/devices/i2c-2/2-0038/name")
        if re.search(r'.*pcf8574a.*',gpio):
            print( "PASSED" )
        else:
            raise Exception( "GPIO expander failed." )

    @label("XIO...\n chinese")
    @progress(60)
    @timeout(15)

    def test_008_xio(self):
        GPIO = 408
        while GPIO < 415:
            print( "Testing XIO pin " + str(GPIO) + "..." ),
            self.ser.send( "echo " + str( GPIO ) + " > /sys/class/gpio/export")
            self.ser.send( "echo " + str( GPIO+1 ) + " > /sys/class/gpio/export")
            self.ser.send( "echo \"out\" > /sys/class/gpio/gpio" + str(GPIO) + "/direction" )
            self.ser.send( "echo 1 > /sys/class/gpio/gpio" + str(GPIO) + "/active_low")
            self.ser.send( "echo 1 > /sys/class/gpio/gpio" + str(GPIO) + "/value")
            self.ser.send( "echo \"in\" > /sys/class/gpio/gpio" + str(GPIO+1) + "/direction")
            self.ser.send( "echo 1 > /sys/class/gpio/gpio" + str(GPIO+1) + "/active_low")
            result = self.ser.send( "cat /sys/class/gpio/gpio" + str(GPIO+1) + "/value")
            if result == "1":
                print( "PASSED" )
            else:
                raise Exception( "XIO failed." )

            self.ser.send( "echo " + str(GPIO) + " > /sys/class/gpio/unexport" )
            self.ser.send( "echo " + str(GPIO+1) + " > /sys/class/gpio/unexport" )
            GPIO+=2

    @label("Stress testing...\n chinese")
    @progress(60)
    @timeout(15)

    def test_009_stress(self):
        print( "Starting stress test..." )
#         time.sleep(0.5)
        stress = self.ser.send("stress --cpu 8 --io 4 --vm 2 --vm-bytes 128M --timeout 10s")
        if re.search(r'.*successful run completed.*',stress):
            print( "STRESS TEST PASSED\n")
        else:
            print "result was " + stress
            raise Exception( "Stress test failed." )

def main():
    tl = TestLoader()
    suite = tl.loadTestsFromTestCase(FactoryHardwareTest)
    result = TextTestRunner(verbosity=2, failfast=True).run(suite) # This runs the whole suite of tests. For now, using TextTestRunner
    print result

#------------------------------------------------------------------
if __name__ == "__main__":
#------------------------------------------------------------------
  exit( main() )

#!/usr/bin/env python
from serialconnection import SerialConnection
import re
import time

class FactoryHardwareTest:
    def __init__(self):
        try:
            self.error = 0
            self.ser = SerialConnection()
            self.initalTest()

            self.wlanTest(0)
            self.wlanTest(1)
            self.wlanTest(2)
            self.wlanEnumTest()

            self.i2cTest(0)
            self.i2cTest(1)
            self.i2cTest(2)
            self.hardwareListTest()

            self.AXPtest()

            self.gpioExpanderTest()

            self.xioTest()

            self.stressTest()

        except Exception, e:
            self.error+=1
            print( "FAILED TO CONNECT TO CHIP!")

    def initalTest(self):
        print( "Waiting for CHIP to boot...")
        hostname = self.ser.send("hostname",timeout=90)
        print hostname
        if re.search(r'.*chip.*',hostname):
            print( "CHIP FOUND! Running tests...")
        else:
            self.error+=1
            print( "FAILED! Hostname not found." )

    def hardwareListTest(self):
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
            print( "FAILED!!!")
            self.error+=1

    def wlanTest(self, x):
        print( "Testing WLAN" + str(x) + "..."),
        wlan = self.ser.send("sudo ip link set wlan0 up")
        code = self.ser.send("echo $?")
        if( code == "0" ):
            print( "PASSED" )
        else:
            self.error+=1
            print( "FAILED!!!" )

    def i2cTest(self,x):
        print( "Testing I2C" + str(x) + "..."),
        i2c = self.ser.send("i2cdetect -y " + str(x))
        bPassed = False

        if x == 0 and re.search(r'.*UU.*',i2c):
            bPassed = True
        elif x == 1 and re.search(r'.* 50 .*',i2c):
            bPassed = True
        elif x == 2 and re.search(r'.*UU.*',i2c) and re.search(r'.* 50 .*',i2c):
            bPassed = True 

        if bPassed:
            print( "PASSED" )
        else:
            self.error+=1
            print( "FAILED!!!" )

    def wlanEnumTest(self):
        print( "Testing WLAN enum..."),
        wlan = self.ser.send("iw dev|grep -v addr |grep -v ssid")
        wlanCompare = self.ser.send("cat /usr/lib/hwtest/wifi_ref0.txt")
        wlan = ''.join(wlan.split())
        wlanCompare = ''.join(wlanCompare.split())
        if re.search(r'.*' + wlanCompare + '.*',wlan):
            print( "PASSED")
        else:
            self.error+=1
            print( "FAILED!!!")

    def AXPtest(self):
        print( "Testing AXP209..."),
        axp = self.ser.send("dmesg |grep axp |sed -e 's/\[.*\]//'")
        axpCompare = self.ser.send("cat /usr/lib/hwtest/axp_ref.txt")
        if re.search(r'.*' + axpCompare + '.*',axp):
            print( "PASSED")
        else:
            self.error+=1
            print( "FAILED!!!")

    def gpioExpanderTest(self):
        print( "Testing GPIO expander..."),
        gpio = self.ser.send("cat /sys/bus/i2c/devices/i2c-2/2-0038/name")
        if re.search(r'.*pcf8574a.*',gpio):
            print( "PASSED" )
        else:
            self.error+=1
            print( "FAILED!!!" )

    def xioTest(self):
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
                self.error+=1
                print( "FAILED!!!" )

            self.ser.send( "echo " + str(GPIO) + " > /sys/class/gpio/unexport" )
            self.ser.send( "echo " + str(GPIO+1) + " > /sys/class/gpio/unexport" )
            GPIO+=2


    def stressTest(self):
        print( "Starting stress test..." )
        time.sleep(0.5)
        stress = self.ser.send("stress --cpu 8 --io 4 --vm 2 --vm-bytes 128M --timeout 10s")
        if re.search(r'.*successful run completed.*',stress):
            print( "STRESS TEST PASSED\n")
        else:
            self.error+=1
            print( "STRESS TEST FAILED!!!\n")

def main():
    test = FactoryHardwareTest()
    if( test.error > 0 ):
        print ( "!!!! TEST FAILED - TOTAL ERRORS: " + str( test.error ) + " !!!!")
    else:
        print( "Test completed! ALL PASSED")
#------------------------------------------------------------------
if __name__ == "__main__":
#------------------------------------------------------------------
  exit( main() )

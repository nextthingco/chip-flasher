#!/usr/bin/env python
from serialconnection import SerialConnection
from unittest import TestCase, TextTestRunner, TestLoader
from observable_test import *
from commandRunner import CommandRunner
from deviceDescriptor import DeviceDescriptor
from nand import *
import os
import re
import time
import io
import serial
from ui_strings import *

LOGIN = 'root'
PASSWORD = 'chip'
ALL_TESTS_PASSED_REGEX = re.compile(r'.*### ALL TESTS PASSED ###.*')

dummy = DeviceDescriptor.makeDummy()

CONNECT_TIME = 60
FINE_SERIAL_TIME = 45

#These erroer codes correspond to the ERROR messages echoed by the hwtest.sh script
#Note that 301 is for no device found. 
errorCodeMap = { \
    "Turn on wlan0": 302,
    "Turn on wlan1": 303,
    "Hardware list": 304,  
    "I2C bus 0": 305,
    "I2C bus 1": 306,
    "I2C bus 2": 307,
    "testing AXP209 on I2C bus 0": 308,
    "GPIO expander test": 309,
    "Doing 10s stress test": 310,
    "Wifi enumeration test": 311,
    "Checking bitflips on NAND": 312
}

# Check to make sure that the tests are all run. If a test is not found, then return it and its code
def checkForMissingTests(str):
    for text,code in errorCodeMap.iteritems():
        if not text in str:
            return text, code 
    return "",0
    
ERROR_REGEX = re.compile("\# (.*)\.\.\.ERROR")
# This is Alex's code. 
#------------------------------------------------------------------
def answer_prompt(sio,prompt_to_wait_for,answer_to_write,send_cr=True):
#------------------------------------------------------------------
  sio.flush()
  prompt_found = False
  data = ''
  #if send_cr:
    #sio.write(unicode('\n'))

  d='something'
  while not len(d)==0:
    d = sio.read(2000);
    data += d
    print '-' * 50
    print ' %d bytes read' % (len(data))
    print '-' * 50

  print data

  while not prompt_found:
    d = sio.read(100);
    data += d
    print '-' * 50
    print ' %d bytes read' % (len(data))
    print '-' * 50
    if(data[:-1].endswith(prompt_to_wait_for)):
        sio.write(unicode(answer_to_write+'\n'))
        print '-' * 50
        print ' detected [%s] ' % prompt_to_wait_for
        print '-' * 50
        prompt_found = True
    else:
        if send_cr:
          sio.write(unicode('\n'))
    sio.flush()
    #sys.stdin.readline()

#------------------------------------------------------------------
def scanfor(sio,regexp_to_scan_for,answer_to_write):
#------------------------------------------------------------------
  prompt_found = False
  data = ''
  while not prompt_found:
    data += sio.read(100);
    print '-' * 50
    print ' %d bytes read' % (len(data))
    print '-' * 50
    print data
    if re.search(regexp_to_scan_for,data):
        print '-' * 50
        print ' detected [%s] ' % regexp_to_scan_for
        print '-' * 50
        sio.write(unicode(answer_to_write+'\n'))
        prompt_found = True
    sio.flush()
  return data


#------------------------------------------------------------------
def test(serial_port):
#------------------------------------------------------------------

  print 'reading from %s:' % serial_port

  ser = serial.Serial(serial_port,115200, timeout=1);
  sio = io.TextIOWrapper(io.BufferedRWPair(ser,ser))

  #login

  answer_prompt(sio,'login:','root')
  answer_prompt(sio,'Password:','chip',False)
  answer_prompt(sio,'#','hwtest')
  d=scanfor(sio,r'.*### [^#]+ ###.*','poweroff')
  ser.close()
  
  missingText, missingCode = checkForMissingTests(d)
  if missingCode != 0:
      print "---> MISSING TEST " + missingText
      return missingCode + 50,d # return 50 more than the error for the code itself
      
  #see the results of the bit flip test    
  if not bitFlipTest(d):
    return errorCodeMap["Checking bitflips on NAND"],d


  if re.search(r'.*### ALL TESTS PASSED ###.*',d):
    print "---> TESTS PASSED"
    return 0, d
    
  match = ERROR_REGEX.search(d)
  errorCode = 300 # this is a default which should't happen
  if match:
      code = match.group(1) #use the first one found for now
      if code in errorCodeMap: #this should not be necessary to test
          errorCode = errorCodeMap[code]
  print "---> TESTS FAILED"
  return errorCode , d

# A regex to search for the checking text followed by 3 decimal numbers
BITFLIP_REGEX = re.compile("\# Checking bitflips on NAND\.\.\.\s([-+]?[0-9]*\.?[0-9]+.)\s*([-+]?[0-9]*\.?[0-9]+.)\s*([-+]?[0-9]*\.?[0-9]+.)")
def bitFlipTest(str):
    match = BITFLIP_REGEX.search(str)
    if not match: #this should not happen
        print "Error, could not parse the bitflip info"
        return False
    uncorrectableBitflips = float(match.group(1))
    correctableBitflips = float(match.group(2))
    rmsCorrectableBitflips = float(match.group(3))
    
    return ( uncorrectableBitflips <= MAX_UNCORRECTABLE_BITFLIPS and 
        correctableBitflips <= MAX_CORRECTABLE_BITFLIPS and 
        rmsCorrectableBitflips <= MAX_RMS_CORRECTABLE_BITFLIPS)
        
    
    
    # Checking bitflips on NAND... 0 49.9 1.64012

#end of Alex's code
class ChipHardwareTest(TestCase):
    '''
    This will wait for CHIP to boot up, log in, and then run 'hwtest' on it
    '''

    def setUp(self):
        self.progressObservers = []
        try:
            self.deviceDescriptor = self.attributes['deviceDescriptor']
        except: # run from regular unit test
            global dummy
            self.deviceDescriptor = dummy # a dummy object
            self.deviceDescriptor.serial = "/dev/chip-2-1-serial"
    
    def findSerialDevice(self):
#         print "find serial device"
#         print self.deviceDescriptor.serial
        return os.path.exists(self.deviceDescriptor.serial)

 
        
    @label(UI_WAITING_FOR_DEVICE)
    @progress(FINE_SERIAL_TIME)
    @failMessage(FAIL_301_TEXT)
    def test_000_serial(self):
        for attempt in range(1,FINE_SERIAL_TIME):
            if self.findSerialDevice():
                return
            time.sleep(1)
        raise Exception("No Serial device found: " + self.deviceDescriptor.serial)
    
    @label(UI_HARDWARE_TEST)
    @progress(45)
    @failMessage(FAIL_302_TEXT)
    def test_020_hwtest(self):
        result, details = test(self.deviceDescriptor.serial)
        if not hasattr(self,"output"):
            self.output = ""
        self.output += details
        if result != 0:
            self.errorCode = result #store it away for later use
        self.assertEqual(0,result)

def main():
    tl = TestLoader()
    suite = tl.loadTestsFromTestCase(ChipHardwareTest)
    result = TextTestRunner(verbosity=2, failfast=True).run(suite) # This runs the whole suite of tests. For now, using TextTestRunner
    print result

#------------------------------------------------------------------
if __name__ == "__main__":
#------------------------------------------------------------------
  exit( main() )

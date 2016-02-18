#!/usr/bin/env python
# from serialconnection import SerialConnection
from unittest import TestCase, TextTestRunner, TestLoader
from observable_test import *
from commandRunner import CommandRunner
from deviceDescriptor import DeviceDescriptor
from config import *
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


HW_ADDR_CMD = "echo -n 'mac=' && ifconfig wlan0 | grep HWaddr | gawk '{print $5}'" #gets a value like: mac=7c:c7:09:10:23:5e
HW_ADDR_REGEX = re.compile(r"mac=([\da-fA-F:]{14})") #parse out the mac address

#These erroer codes correspond to the ERROR messages echoed by the hwtest.sh script
#Note that 301 is for no device found.
errorCodeMap = {
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
    "Checking bit flips on NAND": 312,
    "Checking bad blocks on NAND": 313
}
ERROR_REGEX = re.compile("\# (.*)\.\.\.ERROR")

# A regex to search for the checking text followed by 3 decimal numbers
BITFLIP_REGEX = re.compile(
    "\# Checking bit flips on NAND\.\.\.\s([-+]?[0-9]*\.?[0-9]+.)\s*([-+]?[0-9]*\.?[0-9]+.)\s*([-+]?[0-9]*\.?[0-9]+.)")

# A regex to search for the bad blocks text followed by 2 integers
BAD_BLOCK_REGEX = re.compile(
    "\# Checking bad blocks on NAND\.\.\.\s(\d+)\s(\d+)")

class ChipHardwareTest(TestCase):
    '''
    This will wait for CHIP to boot up, log in, and then run 'hwtest' on it
    '''


    def checkForMissingTests(self,searchStr):
        '''
        Check to make sure that the tests are all run. If a test is not found,
        then return it and its code
        '''
        for text, code in errorCodeMap.iteritems():
            if not text in searchStr:
                return text, code
        return "", 0

    def answer_prompt(self,sio, prompt_to_wait_for, answer_to_write, send_cr=True):
        #------------------------------------------------------------------
        sio.flush()
        prompt_found = False
        data = ''

        d = 'something'
        while not len(d) == 0:
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
                sio.write(unicode(answer_to_write + '\n'))
                print '-' * 50
                print ' detected [%s] ' % prompt_to_wait_for
                print '-' * 50
                prompt_found = True
            else:
                if send_cr:
                    sio.write(unicode('\n'))
            sio.flush()


    def scanfor(self,sio, regexp_to_scan_for, answer_to_write):
        prompt_found = False
        data = ''
        while not prompt_found:
            data += sio.read(100);
            print '-' * 50
            print ' %d bytes read' % (len(data))
            print '-' * 50
            print data
            if re.search(regexp_to_scan_for, data):
                print '-' * 50
                print ' detected [%s] ' % regexp_to_scan_for
                print '-' * 50
                sio.write(unicode(answer_to_write + '\n'))
                prompt_found = True
            sio.flush()
        return data


    def hwtest(self,serial_port):
        print 'reading from %s:' % serial_port

        ser = serial.Serial(serial_port, 115200, timeout=1);
        sio = io.TextIOWrapper(io.BufferedRWPair(ser, ser))

        #login

        self.answer_prompt(sio, 'login:', 'root')
        self.answer_prompt(sio, 'Password:', 'chip', False)
        self.answer_prompt(sio, '#', HW_ADDR_CMD+ ' && hwtest') #easiest to chain together commands

#         self.answer_prompt(sio, '#', 'hwtest')
        d = self.scanfor(sio, r'.*### [^#]+ ###.*', 'poweroff')
        ser.close()

        self.hwAddr(d)

        missingText, missingCode = self.checkForMissingTests(d)
        if missingCode != 0:
            print "---> MISSING TEST " + missingText
            # return 50 more than the error for the code itself
            return missingCode + 50, d

        #get results of the bit flip test and bad block
        bitFlipResult = self.bitFlipTest(d)
        badBlockResult = self.badBlockTest(d)

        if not bitFlipResult:
            return errorCodeMap["Checking bit flips on NAND"], d

        if not badBlockResult:
            return errorCodeMap["Checking bad blocks on NAND"], d

        if re.search(r'.*### ALL TESTS PASSED ###.*', d):
            print "---> TESTS PASSED"
            return 0, d

        match = ERROR_REGEX.search(d)
        errorCode = 300  # this is a default which should't happen
        if match:
            code = match.group(1)  # use the first one found for now
            if code in errorCodeMap:  # this should not be necessary to test
                errorCode = errorCodeMap[code]
        print "---> TESTS FAILED"
        return errorCode, d

    def hwAddr(self,searchStr):
        match = HW_ADDR_REGEX.search(searchStr)
        if not match:  # this should not happen
            print "Error, could not parse the mac address"
        else:
            hwAddr = match.group(1)
            self.returnValues['hwAddr'] = hwAddr
            print "MAC: " + hwAddr

    def bitFlipTest(self,searchStr):
        '''
        Parses:
        # Checking bit   flips on NAND... 0 49.9 1.64012
        '''
        match = BITFLIP_REGEX.search(searchStr)
        if not match:  # this should not happen
            print "Error, could not parse the bit  flip info"
            return False
        uncorrectableBitflips = float(match.group(1))
        correctableBitflips = float(match.group(2))
        stdDevCorrectableBitflips = float(match.group(3))
        self.returnValues['uncorrectableBitflips'] = uncorrectableBitflips
        self.returnValues['correctableBitflips'] = correctableBitflips
        self.returnValues['stdDevCorrectableBitflips'] = stdDevCorrectableBitflips

        return (uncorrectableBitflips <= MAX_UNCORRECTABLE_BITFLIPS and
                correctableBitflips <= MAX_CORRECTABLE_BITFLIPS and
                stdDevCorrectableBitflips <= MAX_STD_DEV_CORRECTABLE_BITFLIPS)

    def badBlockTest(self,searchStr):
        '''
        Parses:
        # Checking bad blocks on NAND... 52 4
        '''
        print searchStr
        match = BAD_BLOCK_REGEX.search(searchStr)
        if not match:  # this should not happen
            print "Error, could not parse the bad block info"
            return False
        badBlocks = int(match.group(1))
        bbtBlocks = int(match.group(2))
        self.returnValues['badBlocks'] = badBlocks
        self.returnValues['bbtBlocks'] = bbtBlocks
        print "bad blocks " + str(badBlocks) + " bbt blocks " + str(bbtBlocks)
        return (badBlocks <= MAX_BAD_BLOCKS and
                bbtBlocks >= MIN_BBT_BLOCKS)


    def setUp(self):
        self.progressObservers = []
#         self.returnValues['uncorrectableBitflips'] = -1
#         self.returnValues['correctableBitflips'] = 0
#         self.returnValues['stdDevCorrectableBitflips'] = 0
#         self.returnValues['badBlocks'] = 0
#         self.returnValues['bbtBlocks'] = 0

        try:
            self.deviceDescriptor = self.attributes['deviceDescriptor']
        except:  # run from regular unit test
            global dummy
            self.deviceDescriptor = dummy  # a dummy object
            self.deviceDescriptor.serial = "/dev/chip-2-1-serial"

    def findSerialDevice(self):
        #         print "find serial device"
        #         print self.deviceDescriptor.serial
        return os.path.exists(self.deviceDescriptor.serial)

    @label(UI_WAITING_FOR_DEVICE)
    @progress(FIND_SERIAL_TIME)
    @errorNumber(301)
    @failMessage(FAIL_301_TEXT)
    def test_000_serial(self):
        for attempt in range(1, FIND_SERIAL_TIME):
            if self.findSerialDevice():
                return
            time.sleep(1)
        raise Exception(
            "No Serial device found: " + self.deviceDescriptor.serial)

    @label(UI_HARDWARE_TEST)
    @progress(62)
    @errorNumber(302)
    @failMessage(FAIL_302_TEXT)
    def test_020_hwtest(self):
        result, details = self.hwtest(self.deviceDescriptor.serial)
        if not hasattr(self, "output"):
            self.output = ""
        self.output += details
        if result != 0:
            self.errorCode = result  # store it away for later use
        self.assertEqual(0, result)

    @classmethod
    def statsTableName(cls):
        return "hwtest"

    CUSTOM_COLUMNS = [
                      ['hwAddr','TEXT',""],
                      ['uncorrectableBitflips','REAL',-1],
                      ['correctableBitflips','REAL',-1],
                      ['stdDevCorrectableBitflips','REAL',-1],
                      ['badBlocks','INTEGER',-1],
                      ['bbtBlocks','INTEGER',-1]
                    ]

    @classmethod
    def statsTableColumns(cls):
        return cls.CUSTOM_COLUMNS

    @staticmethod
    def getStatsQueries(where):
        table = ChipHardwareTest.statsTableName()
        return [
            "select count(*) as 'total', sum(1-result) as 'failed', sum(result) as 'passed' from {0} where {1}".format(table,where),
            "select avg(elapsedTime) as 'averageTime' from {0} where result=1 AND {1}".format(table,where),
            "select avg(uncorrectableBitflips) from {0} where uncorrectableBitflips != -1 AND {1}".format(table,where),
            "select avg(correctableBitflips) from {0} where correctableBitflips != -1 AND {1}".format(table,where),
            "select avg(badBlocks) from {0} where badBlocks != -1 AND {1}".format(table,where),
            "select avg(bbtBlocks) from {0} where bbtBlocks != -1 AND {1}".format(table,where),
            "select error as errors_key, count(error) as errors_val from {0} where error != 0 and {1} group by error order by error".format(table,where)
        ]
def main():
    tl = TestLoader()
    suite = tl.loadTestsFromTestCase(ChipHardwareTest)
    # This runs the whole suite of tests. For now, using TextTestRunner
    result = TextTestRunner(verbosity=2, failfast=True).run(suite)
    print result

if __name__ == "__main__":
    exit(main())

# -*- coding: utf-8 -*-

from unittest import TestCase, TextTestRunner, TestLoader
import logging
import sys
from observable_test import *
import threading
import os.path
# from pytest_timeout import *
# from observable_test import label
# from observed import observable_method
from commandRunner import CommandRunner

import random
serialLog = logging.getLogger("serial")
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

FEL = 'fel'
class Upload(TestCase):
    @classmethod
    def setUpClass(cls):
        print ("upload set up")
#         cls.felLock = threading.Lock()
        
    err_codes = {
        -1: "Unknown Failure",
        128: "FEL Error.",
        129: "DRAM Error?",
        130: "Upload Error.",
        131: "Upload Error.",
        132: "Bad Cable?",
        133: "Fastboot fail.",
        134: "Fastboot fail.",
        135: "Bad U-boot."
    }
    
    
    def setUp(self):
        self.progressObservers = []
        try:
            self.felPort = self.attributes['deviceDescriptor'].fel
            self.felLock = self.attributes['felLock']
        except: # run from regular unit test
            from threading import Lock
            self.felPort = "/dev/chip_usb"
            self.felLock = threading.Lock()
#        print("Waiting for USB")
#         if not wait_for_fel( instance=None, type="fel", serialLog=serialLog, timeout=30 ):
#             raise Exception( "Flashing failed: ", "Could not find FEL device" )
        pass  
    
    def findFelDevice(self):
        return os.path.isfile(self.felPort)
        
        
        
    def _doFlashStage(self,stage, chipPath=None,timeout=400):
        if True:
            time.sleep(1)
            if random.random() < 0.1:
                raise Exception("mock failure on " + self.felPort)
            return
        
        commandRunner = CommandRunner(serialLog,progressObservers = self.progressObservers)
        args = ["./chip-flash","-u", ".firmware", "--stage",str(stage)]
        if chipPath:
            args.extend(["--chip-path", chipPath])
        errcode = commandRunner.call_and_return(cmd=args, timeout=timeout)
        print("Error code: " + str(errcode) )
        if errcode != 0:
            if not errcode in self.err_codes:
                errcode = -1
            raise Exception( "Flashing failed: ", self.err_codes[ errcode ] )
        
    
    @label("Waiting for FEL\n chinese")
    @progress(10)
    def test_0_fel(self):
        for attempt in range(1,10):
            if self.findFelDevice():
                return
            time.sleep(1)
        raise Exception("No FEL device found")
            
        
        
    @label("Launch SPL\n chinese")
    @progress(5)
    def test_Stage0(self):
        with self.felLock:
            self._doFlashStage(0)

    @label("Upload SPL\n chinese")
    @progress(5)
    def test_Stage1(self):
        with self.felLock:
            self._doFlashStage(1)
        
    @label("Upload U-Boot\n chinese")
    @progress(5)
#     @promptAfter("after upload UbootL")
    def test_Stage2(self):
        with self.felLock:
            self._doFlashStage(2)
        
    @label("Upload U-Boot Script\n chinese")
    @progress(5)
    def test_Stage3(self):
        with self.felLock:
            self._doFlashStage(3)
    
    @label("Execute U-Boot\n chinese")
    @progress(60)
    def test_Stage4(self):
        with self.felLock:
            self._doFlashStage(4)

    @label("Upload UBI\n chinese")
    @progress(210)
    def test_Stage5(self):
        self._doFlashStage(5)
        
def main():
    tl = TestLoader()
    suite = tl.loadTestsFromTestCase(Upload)
    result = TextTestRunner(verbosity=2, failfast=True).run(suite) # This runs the whole suite of tests. For now, using TextTestRunner
    print result

#------------------------------------------------------------------
if __name__ == "__main__":
#------------------------------------------------------------------
  exit( main() )

    
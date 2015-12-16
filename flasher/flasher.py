#!/usr/bin/env python
from unittest import TestCase, TextTestRunner, TestLoader
import logging
import sys
import os.path
from kivy import Logger
import random #for mocking
from ui_strings import *
from observable_test import *
from commandRunner import CommandRunner

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

MOCK = False #For testing GUI without real things plugged in
class Flasher(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.log = Logger
        cls.timeoutMultiplier = 1.0

        
    err_codes = {
        -1: "Unknown Failure",
        128: "FEL Error.",
        129: "DRAM Error?",
        130: "Flasher Error.",
        131: "Flasher Error.",
        132: "Bad Cable?",
        133: "Fastboot fail.",
        134: "Fastboot fail.",
        135: "Bad U-boot."
    }
    
    
    def setUp(self):
        self.progressObservers = []
        try:
            self.felPort = self.attributes['deviceDescriptor'].fel
        except: # run from regular unit test
            self.felPort = "/dev/ttyACM0"
    
    def findFelDevice(self):
        if MOCK:
            return True
        return os.path.exists(self.felPort)
        
# Uncomment for mocking        
    def _doFlashStageMock(self,stage,timeout=400):
        if True:
            time.sleep(stage)
            if random.random() < 0.1:
                self.fail("Mock Failure")
            return
         
    def _doFlashStage(self,stage,timeout=400):
        if MOCK:
            return self._doFlashStageMock(stage,timeout)
        timeout = timeout * self.timeoutMultiplier
        
        print "_doFlashStage timeout " + str(timeout)
        commandRunner = CommandRunner(self.log,progressObservers = self.progressObservers)
        args = ["./chip-flash","-u", ".firmware", "--stage",str(stage)]
        if self.felPort:
            args.extend(["--chip-path", self.felPort])
        print self.felPort
        print args
        out, errcode = commandRunner.call_and_return(cmd=args, timeout=timeout)
        if not hasattr(self,"output"):
            self.output = ""
        self.output += out
        if errcode != 0:
            if not errcode in self.err_codes:
                errcode = -1
            self.output += "\nFlashing failed: " + self.err_codes[ errcode ] + "\n"
            raise Exception( "Flashing failed: ", self.err_codes[ errcode ] )
        
    
    @label(UI_WAITING_FOR_DEVICE)
    @progress(10)
    @failMessage(FAIL_201_TEXT)
    def test_0_fel(self):
        for attempt in range(1,10):
            if self.findFelDevice():
                return
            time.sleep(1)
        raise Exception("No FEL device found: " + self.felPort)
            
        
        
    @label(UI_LAUNCH_SPL)
    @progress(8)
    @mutex("fel")
    @failMessage(FAIL_202_TEXT)
    def test_Stage0(self):
        self._doFlashStage(0)

    @label(UI_UPLOAD_SPL)
    @progress(7)
    @mutex("fel")
    @failMessage(FAIL_202_TEXT)
    def test_Stage1(self):
        self._doFlashStage(1)
        
    @label(UI_UPLOAD_UBOOT)
    @progress(2)
    @failMessage(FAIL_202_TEXT)
    def test_Stage2(self):
        self._doFlashStage(2)
        
    @label(UI_UPLOAD_UBOOT_SCRIPT)
    @progress(1)
    @failMessage(FAIL_202_TEXT)
    def test_Stage3(self):
        self._doFlashStage(3)
    
    @label(UI_EXECUTE_UBOOT_SCRIPT)
    @progress(1)
    @failMessage(FAIL_202_TEXT)
    def test_Stage4(self):
        self._doFlashStage(4)

    @label(UI_UPLOAD_UBI)
    @progress(345)
    @failMessage(FAIL_203_TEXT)
    def test_Stage5(self):
        self._doFlashStage(5, timeout = 400)
        
def main():
    tl = TestLoader()
    suite = tl.loadTestsFromTestCase(Flasher)
    result = TextTestRunner(verbosity=2, failfast=True).run(suite) # This runs the whole suite of tests. For now, using TextTestRunner
    print result

#------------------------------------------------------------------
if __name__ == "__main__":
#------------------------------------------------------------------
  exit( main() )

    
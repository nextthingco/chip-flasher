#!/usr/bin/env python
from unittest import TestCase, TextTestRunner, TestLoader
import logging
import sys
from observable_test import *
import threading
import os.path
from kivy import Logger
import pexpect    
from os import path
from os import environ
from ui_strings import *
# from pytest_timeout import *
# from observable_test import label
# from observed import observable_method
from commandRunner import CommandRunner

import random
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

FEL = 'fel'
class Flasher(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.log = Logger
        cls.log.info("upload class set up")
        
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
        print self.felPort
        return os.path.exists(self.felPort)
        
        
# Uncomment for mocking        
#     def _doFlashStage(self,stage,timeout=400):
#         if True:
#             time.sleep(1)
#             if random.random() < 0.1:
#                 raise Exception("mock failure on " + self.felPort)
#             return
         
    def _doFlashStage(self,stage,timeout=400):
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
        
#     def _doFlashStageNew(self,stage,timeout=400):
#         args = ["-u", ".firmware", "--stage",str(stage)]
#         
#         if self.felPort:
#             args.extend(["--chip-path", self.felPort])
#         cmd = "bash ./chip-py " + " ".join(args)
#         working_dir=path.dirname( path.dirname( path.realpath( __file__ ) ) )
#         cwd = working_dir + "/flasher/tools"
#         my_env = os.environ.copy()
#         my_env["BUILDROOT_OUTPUT_DIR"] = cwd+"/.firmware/"
#         output, errcode = pexpect.run(cmd, cwd = cwd, withexitstatus = True, timeout = timeout, env = my_env)
#         self.output += output
#         if errcode != 0:
#             if not errcode in self.err_codes:
#                 errcode = -1
#             raise Exception( "Flashing failed: ", self.err_codes[ errcode ] )
    
    @label(UI_WAITING_FOR_DEVICE)
    @progress(10)
    def test_0_fel(self):
        for attempt in range(1,10):
            if self.findFelDevice():
                return
            time.sleep(1)
        raise Exception("No FEL device found: " + self.felPort)
            
        
        
    @label(UI_LAUNCH_SPL)
    @progress(5)
    def test_Stage0(self):
        self._doFlashStage(0)

    @label(UI_UPLOAD_SPL)
    @progress(5)
    @mutex("fel")
    def test_Stage1(self):
        self._doFlashStage(1)
        
    @label(UI_UPLOAD_UBOOT)
    @progress(5)
    def test_Stage2(self):
        self._doFlashStage(2)
        
    @label(UI_UPLOAD_UBOOT_SCRIPT)
    @progress(5)
    def test_Stage3(self):
        self._doFlashStage(3)
    
    @label(UI_EXECUTE_UBOOT_SCRIPT)
    @progress(60)
    def test_Stage4(self):
        self._doFlashStage(4)

    @label(UI_UPLOAD_UBI)
    @progress(210)
    def test_Stage5(self):
        self._doFlashStage(5)
        
def main():
    tl = TestLoader()
    suite = tl.loadTestsFromTestCase(Flasher)
    result = TextTestRunner(verbosity=2, failfast=True).run(suite) # This runs the whole suite of tests. For now, using TextTestRunner
    print result

#------------------------------------------------------------------
if __name__ == "__main__":
#------------------------------------------------------------------
  exit( main() )

    
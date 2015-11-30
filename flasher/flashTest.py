# -*- coding: utf-8 -*-

from usb import USB,wait_for_usb
from unittest import TestCase
import logging
import sys
from observable_test import *
# from observable_test import label
# from observed import observable_method
from commandRunner import CommandRunner

log = logging.getLogger("serial")
logging.basicConfig(stream=sys.stdout, level=logging.INFO)


class Upload(TestCase):
    
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
#        print("Waiting for USB")
#         if not wait_for_usb( instance=None, type="fel", log=log, timeout=30 ):
#             raise Exception( "Flashing failed: ", "Could not find FEL device" )
        pass  
    
    
    @label("Waiting to plug in...\n chinese")
    @progress(60)
    @timeout(400)
    def test_000_plugin(self):
        time.sleep(5)

    @label(None)
    def test_001_Idle(self):    
        print "test 001 idle"
        time.sleep(5)
        if not wait_for_usb( instance=None, type="fel", log=log, timeout=30 ):
            raise Exception( "Flashing failed: ", "Could not find FEL device" )
    

    @label("wait for usb")
    @progress(30)
    @timeout(50)
    @promptBefore("Click to begin\n in Chinese")
    def test_01_FEL(self):    
        print "zzzzzzzzzzzclick to begin"
        time.sleep(5)
        if not wait_for_usb( instance=None, type="fel", log=log, timeout=30 ):
            raise Exception( "Flashing failed: ", "Could not find FEL device" )
#
    @label("Uploading...\n正在加载固件")
    @progress(60)
    @timeout(400)
    def test_02_flash(self):
        print("Running chip-fel-flash")
        commandRunner = CommandRunner(log,progressObservers = self.progressObservers)
        errcode = commandRunner.call_and_return(cmd=["./chip-fel-flash.sh", "-f"], timeout=400)
        print("Error code: " + str(errcode) )
        if errcode != 0:
            if not errcode in self.err_codes:
                errcode = -1
            raise Exception( "Flashing failed: ", self.err_codes[ errcode ] )

        

#         
# class TestHardware(ObservableTestCase):
#     
#     def setUp(self):
#         print("Waiting for USB")
#         
#         if not wait_for_usb( instance=Null, type="fel", log=log, timeout=30 ):
#             raise Exception( "Flashing failed: ", "Could not find FEL device" )
#         
#     def run(self):
#         print("Running chip-fel-flash")
#         commandRunner = CommandRunner(log)
#         errcode = commandRunner.call_and_return(cmd=["./chip-fel-flash.sh", "-f"], timeout=400 )
#         errcode = 0
#         print("Error code: " + str(errcode) )
#         if errcode != 0:
#             if not errcode in self.err_codes:
#                 errcode = -1
#             raise Exception( "Flashing failed: ", self.err_codes[ errcode ] )
# 
#     
#     
    
    
    
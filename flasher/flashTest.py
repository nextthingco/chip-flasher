# -*- coding: utf-8 -*-

from unittest import TestCase, TextTestRunner, TestLoader
import logging
import sys
from observable_test import *
# from pytest_timeout import *
# from observable_test import label
# from observed import observable_method
from commandRunner import CommandRunner

serialLog = logging.getLogger("serial")
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
        self.progressObservers = []
#        print("Waiting for USB")
#         if not wait_for_usb( instance=None, type="fel", serialLog=serialLog, timeout=30 ):
#             raise Exception( "Flashing failed: ", "Could not find FEL device" )
        pass  
    
    def _doFlashStage(self,stage,timeout=400):
        commandRunner = CommandRunner(serialLog,progressObservers = self.progressObservers)
        errcode = commandRunner.call_and_return(cmd=["./chip-flash","-u", ".firmware", "--stage",str(stage)], timeout=timeout)
        print("Error code: " + str(errcode) )
        if errcode != 0:
            if not errcode in self.err_codes:
                errcode = -1
            raise Exception( "Flashing failed: ", self.err_codes[ errcode ] )
        
    
    @label("Launch SPL\n chinese")
    @progress(5)
    def test_Stage0(self):
        self._doFlashStage(0)

    @label("Upload SPL\n chinese")
    @progress(5)
    def test_Stage1(self):
        self._doFlashStage(1)
        
    @label("Upload U-Boot\n chinese")
    @progress(5)
    def test_Stage2(self):
        self._doFlashStage(2)
        
#     @label("Upload U-Boot Script\n chinese")
#     @progress(5)
    def test_Stage3(self):
        self._doFlashStage(3)
    
#     @label("Execute U-Boot\n chinese")
#     @progress(60)
    def test_Stage4(self):
        self._doFlashStage(4)

    @label("Upload UBI\n chinese")
    @progress(210)
    @promptAfter("Flashing Finished.\n Press a key")
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

    
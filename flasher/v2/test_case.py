#!/usr/bin/env python

import unittest
from flasher.usb import USB,wait_for_usb
class ObservableTestCase(unittest.TestCase):
    
    def __init__(self, *args, **kwargs):
         super(ObservableTestCase, self).__init__(*args, **kwargs)
         self.observers = []
         
    def addObserver(self, observer):
        print "adding observer"
        self.observers += observer
             
    def run(self,result=None):
#         try:
            
        print "running test "
        super(ObservableTestCase,self).run(result)

#     def __init__(self,name):
#         self.name = name
#         self.log = None
        
    def findUsb(self):
        print("Waiting for USB")
        
        if not wait_for_usb( type="fel", log=self.log, timeout=30 ):
            raise Exception( "Flashing failed: ", "Could not find FEL device" )

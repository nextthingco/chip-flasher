#!/usr/bin/env python

from flasher.serialconnection import SerialConnection
import re
from test_case import ObservableTestCase
from obsub import event
class HardwareTest(ObservableTestCase):
    def __init__(self,name):
        ObservableTestCase.__init__(self, name)
        self.ser = None #maybe pass one in?

    @event
    def setUp (self):
        if not self.ser:
            try:
                self.ser = SerialConnection()
                if not self.ser.doLogin():
                    self.fail("Could not create serial connection. (false)")
            except:
                self.fail("Could not create serial connection. (except)")

    @event        
    def tearDown (self):
        self.ser = None # will call destructor
  
    @event    
    def runTest(self):
        try:
            hostname = self.ser.send("hostname")
            print hostname
            hwTestResult = self.ser.send("ls -l",timeout=60)
            print hwTestResult
    #         ser.send("poweroff",blind=True);
        
            if re.search(r'.*### ALL TESTS PASSED ###.*',hwTestResult):
                result = 0
                print "---> TESTS PASSED"
            else:
                result = 1
                print "---> TESTS FAILED"
        except Exception, e:
            print e
            print "---> TESTS FAILED - EXCEPTION"
            result =  2
        return result
    


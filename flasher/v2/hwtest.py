#!/usr/bin/env python
# -*- coding: utf-8 -*-

from observable_test import *
from flasher.serialconnection import SerialConnection
import re
from unittest import TestCase
class HardwareTest(TestCase):

    def setUp (self):
        if not self.ser:
            try:
                self.ser = SerialConnection()
                if not self.ser.doLogin():
                    self.fail("Could not create serial connection. (false)")
            except:
                self.fail("Could not create serial connection. (except)")

    def tearDown (self):
        self.ser = None # will call destructor
  
    @label("Verifying...\n验证中" )
    def runTest(self):
        try:
            hostname = self.ser.send("hostname")
            print hostname
            hwTestResult = self.ser.send("hwtest",timeout=60)
            print hwTestResult
            self.ser.send("poweroff",blind=True);
        
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
    


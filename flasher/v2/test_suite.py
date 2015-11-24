#!/usr/bin/env python

import unittest
class TestSuite(unittest.TestSuite):
    def __init__(self, eventListener, devicePort):
        self.eventListener = eventListener
        self.devicePort = devicePort
        
    def addTest(self, test):
        test.setUp += self.eventListener
        test.runTest += self.eventListener
        test.tearDown += self.eventListener
        unittest.TestSuite.addTest(self, test)
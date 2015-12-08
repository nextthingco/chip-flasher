# -*- coding: utf-8 -*-
import sys
from flasher.testSuiteGUIApp import TestSuiteGUIApp

def main(argv):
    if len(argv) == 0:
        print "Must pass in the name of a test suite class"
        exit()
    app = TestSuiteGUIApp(argv[0])
    try:
        app.run()
    except (KeyboardInterrupt, SystemExit):
        app.stop()
    
    
    
if __name__ == '__main__':
    main(sys.argv[1:])

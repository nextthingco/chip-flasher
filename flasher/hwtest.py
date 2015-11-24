#!/usr/bin/env python
from serialconnection import SerialConnection
import re



def hwtest():
    try:
        ser = SerialConnection()
        hostname = ser.send("hostname")
        print hostname
        hwTestResult = ser.send("hwtest",timeout=60)
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
    finally:
        if ser:
            ser.close() 
    return result


def main():
    hwtest()
#------------------------------------------------------------------
if __name__ == "__main__":
#------------------------------------------------------------------
  exit( main() )

#!/usr/bin/env python

import io
import sys
import serial
import re

#------------------------------------------------------------------
def answer_prompt(sio,prompt_to_wait_for,answer_to_write):
#------------------------------------------------------------------
  prompt_found = False
  data = ''
  while not prompt_found:
    data += sio.read(100);
    print '-' * 50
    print ' %d bytes read' % (len(data))
    print '-' * 50
    print data
    if(data[:-1].endswith(prompt_to_wait_for)):
        sio.write(unicode(answer_to_write+'\n'))
        print '-' * 50
        print ' detected [%s] ' % prompt_to_wait_for
        print '-' * 50
        prompt_found = True
    else:
        sio.write(unicode('\n'))
    sio.flush()

#------------------------------------------------------------------
def scanfor(sio,regexp_to_scan_for,answer_to_write):
#------------------------------------------------------------------
  prompt_found = False
  data = ''
  while not prompt_found:
    data += sio.read(100);
    print '-' * 50
    print ' %d bytes read' % (len(data))
    print '-' * 50
    print data
    if re.search(regexp_to_scan_for,data):
        print '-' * 50
        print ' detected [%s] ' % regexp_to_scan_for
        print '-' * 50
        sio.write(unicode(answer_to_write+'\n'))
        prompt_found = True
    sio.flush()
  return data


#------------------------------------------------------------------
def main():
#------------------------------------------------------------------

  if( len(sys.argv)>1 ):
    serial_port=sys.argv[1]
  else:
    serial_port='/dev/ttyACM0';

  print 'reading from %s:' % serial_port

  ser = serial.Serial(serial_port,115200, timeout=1);
  sio = io.TextIOWrapper(io.BufferedRWPair(ser,ser))

  #login

  answer_prompt(sio,'login:','root')
  answer_prompt(sio,'#','hwtest')
  d=scanfor(sio,r'.*### [^#]+ ###.*','poweroff')

  if re.search(r'.*### ALL TESTS PASSED ###.*',d):
    print "---> TESTS PASSED"
    ser.close();
    return 0 
    
  ser.close();
  
  print "---> TESTS FAILED"
  return 1



#------------------------------------------------------------------
if __name__ == "__main__":
#------------------------------------------------------------------
  exit( main() )

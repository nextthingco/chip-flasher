from logging import log
import logging
import os
import serial
import sys
import termios
from pexpect import fdpexpect

COMMAND_PROMPT = "root@chip:~# "
log = logging.getLogger()
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

class SerialConnection(object):
    def __init__(self):
        self.serialDeviceName = "/dev/tty.usbmodem1411"
        self.baudRate = 115200
        self.timeout = 30
        self.spawn = None

    def connect(self):
        try:
  #          fileDescriptor = os.open(self.serialDeviceName, os.O_RDWR|os.O_NONBLOCK|os.O_NOCTTY)

            ser = serial.Serial(self.serialDeviceName,115200) # open the serial port
        except:
            log.error("Could not open serial device: "+self.serialDeviceName)
            return None

#        self.spawn = fdpexpect.fdspawn(fileDescriptor)
        self.spawn = fdpexpect.fdspawn(ser) #, 'wb', timeout=50)

#         # Set the baud rate. See https://www.digi.com/wiki/developer/index.php/Connect_Port_Serial_Port_Access
#         termiosSettings = termios.tcgetattr(fileDescriptor)
#         termiosSettings[4] = self.baudRate; #ispeed
#         termiosSettings[5] = self.baudRate; #ospeed
#         try:
#             termios.tcsetattr(fileDescriptor, termios.TCSADRAIN, termiosSettings)
#         except:
# #            os.close(fileDescriptor)
#             log.error("Could not open " + self.serialDeviceName)
#             return None
        return self.spawn

    def close(self):
        self.spawn.close()

    def login(self):
        if self.spawn is None:
            self.connect()
        term = self.spawn;
        try:
            term.sendLine() #send a blank line
            index = term.expect("chip login: ", timeout=self.timeout)
            term.sendLine("root")
            index = term.expect("Password: ")
            term.sendLine("chip")
            index = term.expect(COMMAND_PROMPT)
        except:
            log.error("unable to log in")
            return None
        return term

    def test(self):
        if not self.login():
            print "error could not login"
            return
        self.spawn.sendLine("ls");
        print self.spawn.before



def main():
    ser = SerialConnection()
    ser.test()
    ser.close()

if __name__ == "__main__":
  exit( main() )

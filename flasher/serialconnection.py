from logging import log
import logging
import os
import serial
import sys
import time
# from usb import USB #it would be nice if we could get the device this way, but I don't see how -HK
# import termios
from pexpect import fdpexpect
import pexpect

COMMAND_PROMPT = '.*@chip.*[$#] '
# COMMAND_PROMPT = '# '
LOGIN = "root"
PASSWORD = "chip"
BAUD=115200
SERIAL_DEVICE_NAME="/dev/chip_usb" 
TIMEOUT = 30

log = logging.getLogger("serial")
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

class SerialConnection(object):
    '''
    Class which manages a serial connection. Once connected, it can be used to send and receive commands
    '''
    
    def __init__(self,login=LOGIN, password=PASSWORD, serialDeviceName=SERIAL_DEVICE_NAME):
        '''
        Constructor
        :param login: remote login
        :param password: remote password
        '''
#         if serialDeviceName is None:
#             self.usb = USB()
#             device = self.usb.find_device("serial-gadget")
#             pass
#             
            
#         usb1.USBContext.getByVendorIDAndProductID(self, vendor_id, product_id, skip_on_access_error, skip_on_error)
        self.login = login;
        self.password = password;
        # self.serialDeviceName = "/dev/tty.usbmodem1421"
        self.serialDeviceName = serialDeviceName
        self.timeout = TIMEOUT #how long commands should wait for until timing out.
        
        self.tty = None
        self.ser = None
        
    def __del__(self):
        self.close()
    
#     def __connectUsingDevice(self):
#         try:
#             fileDescriptor = os.open(self.serialDeviceName, os.O_RDWR | os.O_NONBLOCK | os.O_NOCTTY)
#             log.debug("File descriptor: " + str( fileDescriptor))
#             self.tty = fdpexpect.fdspawn(fileDescriptor)
#             assert (self.tty.isalive())
#             
#             # Set the baud rate. See https://www.digi.com/wiki/developer/index.php/Connect_Port_Serial_Port_Access 
# #             termiosSettings = termios.tcgetattr(fileDescriptor)
# #             termiosSettings[4] = BAUD;  # ispeed
# #             termiosSettings[5] = BAUD;  # ospeed
# #             termios.tcsetattr(fileDescriptor, termios.TCSADRAIN, termiosSettings)  # This is not working on baud rates above 4098
#         except Exception, e:
#             if e.errno == 2:
#                 log.debug("Could not open serial device: " + self.serialDeviceName)
#             else:
#                 log.exception(e)
#             return None

    def __connectUsingSerial(self):
        try:
            self.ser = serial.Serial(port=self.serialDeviceName, baudrate=BAUD, timeout=self.timeout)  # open the serial port. Must make a class member so it won't get cleaned up
        except Exception, e:
            if e.errno == 2:
                log.debug("Could not open serial device: " + self.serialDeviceName)
            else:
                log.exception(e)

        try:
            self.tty = fdpexpect.fdspawn(self.ser)  # , 'wb', timeout=50)
            assert (self.tty.isalive())
        except Exception, e:
            log.debug("Could not open serial device [2]: " + self.serialDeviceName)
            
    def connect(self):
        log.debug("connecting")
        while self.tty == None:
            try:
                self.__connectUsingSerial()
            except Exception,e:
                if e.errno != 2: # device not found
                    log.error("Could not connect")
                    return None
                time.sleep(1)
                
        
        
    def doLogin(self):
        '''
        Logs in if necessary. The result of this call is the remote has a command prompt and is ready
        In reality, only the first call will trigger a login
        '''
        try:
            while True:
                if self.tty is None: #if first time or the session closed on us
                    self.connect()
                    self.tty.sendline("\n\n\n")  # send blank lines to wakeup the device
                    time.sleep(.3) #wait for device to process these empty lines
                try:
                    index = self.tty.expect([".*login: ",".*assword.*", "=>", COMMAND_PROMPT, pexpect.EOF, pexpect.TIMEOUT], timeout=self.timeout)
                except Exception, e:
                    print e
                    if e.errno == 11: #in use error
                        log.error("FATAL")
                        log.exception(e)
                        return False;
                    #this can be benign. There could have been a timeout that caused this
                    self.close()
                    continue # try again. A new connection will be made
                # Go through the various possibilities. The index corresponds to the array passed into expect() above
#                 print self.tty.before
                if index == 0:
                    log.debug("Sending login")
                    self.tty.sendline(self.login)
                elif index == 1:
                    log.debug("Sending password")
                    self.tty.sendline(self.password)
                    time.sleep(2)
                elif index == 2:
                    log.debug("Uboot prompt detected")
                    self.tty.sendline("reset") # Reset CHIP so that we're no longer in the uboot environment.
                    time.sleep(5) # Wait to make sure we're passed the "press any key to stop autoboot" prompt
                    self.tty = None
                elif index == 3:
                    log.debug("Have prompt, logged in")
                    break  # we have a command prompt, either through login or already there
                elif index == 4: #benign, try again
                    log.debug("EOF on login. benign")
                    time.sleep(.1) #wait and try again
                elif index == 5: # The session was closed by the remote.
                    self.close()
        except Exception, e:
            logging.exception(e)
            log.error("unable to log in")
            return False
        return True
        
    def send(self, cmd,  blind=False, timeout = TIMEOUT):
        '''
        Send a command over the connection. It will login if necessary
        :param cmd: The shell command to execute
        :param blind: If should send without waiting for result. Must be used for poweroff
        :return The response from the device. None in case of error
        '''
        delimiter = "END_COMMAND" # careful not to put any special REGEX chars in this string
        if not self.doLogin():
            print "error could not login"
            return None
        try:
            if delimiter:
                cmd = cmd + " && echo " + delimiter + ""
            self.tty.sendline(cmd) #send command to remote
            if (blind): #if don't care about the result. For example, poweroff
                return None

            self.__expect(delimiter+"\r\n", expectTimeout=timeout) #First, expect that the command is echoed back to us. We're not interested in it
            if delimiter:
                self.__expect("" + delimiter + "\r\n" + COMMAND_PROMPT, exact=False) #Now __expect the newline and command prompt
            else:      
                self.__expect("\r\n" + COMMAND_PROMPT) #Now __expect the newline and command prompt
            result = self.tty.before #everything up to the newline and command prompt is our result
            result = result.rstrip("\r\n") #in most cases there will be a new line. Only if the return is blank will it be empty
            self.tty.sendline("") #For next time, we want to have a prompt ready
            return result
        except Exception, e: # This will happen if the command is invalid on the remote. 
            log.exception(e)
            return None
        
    def __expect(self,findString , expectTimeout=TIMEOUT, exact = False):

        index = 0
        start = time.clock()
        end = start + expectTimeout
        step = .1
        
        while index == 0:
            if time.clock() > end: #this timeout behavior isn't really coret since the __expect below has its own timeout
                return None
            time.sleep(step)
            if exact:
                index = self.tty.expect_exact([pexpect.EOF, findString]) 
            else:
                index = self.tty.expect([pexpect.EOF, findString]) 
            
           
    def close(self):
        '''
        Close the connection. Call when you are done. Also gets called if EOF found
        '''
        if self.tty:
            self.tty.close()
        self.tty = None



# Example to test with
def main():
    ser = SerialConnection()
    for i in range(1,2):
        print ser.send("hostname")
        print "result: " + ser.send("ip link set wlan0 up")
        print "____"
#         print ser.send("ps -x")
#         print ser.send("sleep 12; echo hi; ",timeout=1) 
#         ser.send("poweroff",blind=True)
    ser.close()

if __name__ == "__main__":
  exit(main())
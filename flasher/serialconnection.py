from logging import log
import logging
import os
import serial
import sys
import time
import re
# from usb import USB #it would be nice if we could get the device this way, but I don't see how -HK
# import termios
from pexpect import fdpexpect
import pexpect

COMMAND_PROMPT = r'.*chip.*[$#] '
COMMAND_PROMPT_REGEX = re.compile(r'.*chip.*[$#] ')
COMMAND_DELIMETER = "END_COMMAND" # careful not to put any special REGEX chars in this string
DELIMETER_NEW_LINE_REGEX = re.compile(COMMAND_DELIMETER +  r"\r\n")
DELIMITER_NEW_LINE_COMMAND_PROMPT_REGEX = re.compile(COMMAND_DELIMETER + r"\r\n" + COMMAND_PROMPT)

LOGIN_REGEX = re.compile(r".*login: ")
PASSWORD_REGEX = re.compile(r".*assword.*")
UBOOT_REGEX = re.compile(r"=>")
LOGIN_INCORRECT = re.compile(r"Login incorrect")
# COMMAND_PROMPT_REGEX = 'root@chip:~#'
# COMMAND_PROMPT_REGEX = '# '
LOGIN = "root"
PASSWORD = "chip"
BAUD=115200
SERIAL_DEVICE_NAME="/dev/chip_usb" 
TIMEOUT = 10 #this really doesn't do much

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
serialLog = logging.getLogger("serial")

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
        self.loggedIn = False
        self.tty = None
        self.ser = None
    def __del__(self):
        self.close()
    
#     def __connectUsingDevice(self):
#         try:
#             fileDescriptor = os.open(self.serialDeviceName, os.O_RDWR | os.O_NONBLOCK | os.O_NOCTTY)
#             serialLog.debug("File descriptor: " + str( fileDescriptor))
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
#                 serialLog.debug("Could not open serial device: " + self.serialDeviceName)
#             else:
#                 serialLog.exception(e)
#             return None

    def __connectUsingSerial(self):
        try:
            self.ser = serial.Serial(port=self.serialDeviceName, baudrate=BAUD, timeout=self.timeout)  # open the serial port. Must make a class member so it won't get cleaned up
        except Exception, e:
            if e.errno == 2:
                serialLog.debug("Could not open serial device: " + self.serialDeviceName)
            else:
                serialLog.exception(e)

        try:
            self.tty = fdpexpect.fdspawn(self.ser)  # , 'wb', timeout=50)
            assert (self.tty.isalive())
        except Exception, e:
            serialLog.debug("Could not open serial device [2]: " + self.serialDeviceName)
            
    def connect(self):
        serialLog.debug("connecting")
        while self.tty == None:
            try:
                self.__connectUsingSerial()
                if self.doLogin():
                    break
            except Exception,e:
#                 if e.errno != 2 and e.errno != 5: # device not found
                serialLog.debug("Could not connect")
                time.sleep(1) # wait and try again
                return None
                
        
        
    def doLogin(self):
        '''
        Logs in if necessary. The result of this call is the remote has a command prompt and is ready
        In reality, only the first call will trigger a login
        '''
        try:
            sawLogin = False # if already saw login prompt, don't send a second one. This is because login message contains the word login:
            while True:
                if self.tty is None: #if first time or the session closed on us
                    self.connect()
#                     self.tty.sendline("\n")  # send blank lines to wakeup the device
#                     self.tty.sendline("\n\n\n")  # send blank lines to wakeup the device
#                     time.sleep(.3) #wait for device to process these empty lines
                try:
                    index = self.tty.expect_list([LOGIN_REGEX, PASSWORD_REGEX, UBOOT_REGEX, COMMAND_PROMPT_REGEX, pexpect.EOF, pexpect.TIMEOUT,LOGIN_INCORRECT], timeout=self.timeout)
                except Exception, e:
#                     if e.errno == 11: #in use error
                    serialLog.debug("couldn't read, maybe timeout")
                    serialLog.exception(e)
                    return False;
                    #this can be benign. There could have been a timeout that caused this
#                     self.close()
#                     continue # try again. A new connection will be made
                # Go through the various possibilities. The index corresponds to the array passed into expect() above
                serialLog.debug(self.tty.before)
                if index == 0:
                    if sawLogin: # ignore if already saw
                        continue
                    serialLog.debug("Sending login")
                    sawLogin = True
                    self.tty.sendline(self.login)
                    time.sleep(.5)
                elif index == 1:
                    serialLog.debug("Sending password")
                    self.tty.sendline(self.password)
                    time.sleep(2)
                elif index == 2:
                    serialLog.debug("Uboot prompt detected")
                    sawLogin = False
                    self.tty.sendline("reset") # Reset CHIP so that we're no longer in the uboot environment.
                    time.sleep(5) # Wait to make sure we're passed the "press any key to stop autoboot" prompt
                    self.tty = None
                elif index == 3:
                    serialLog.debug("Have prompt, logged in")
                    self.loggedIn = True
                    self.tty.sendline("stty columns 180") #without this, long commands will hang!
                    time.sleep(1) #give this command time to take effect. 
                    break  # we have a command prompt, either through login or already there
                elif index == 4: #benign, try again
                    serialLog.debug("EOF on login. benign")
                    time.sleep(.2) #wait and try again
                    if not sawLogin:
                        serialLog.debug("Sending blank line")
                        self.tty.sendline("")
                elif index == 5: # The session was closed by the remote.
                    self.close()
                elif index == 6:
                    serialLog.debug("Login failed")
                    self.sawLogin = False
                    time.sleep(2)
                 #TODO not working right if faced with the password field at startupf    
        except Exception, e:
            print e
            serialLog.exception(e)
            serialLog.error("unable to serialLog in")
            return False
        return True
        
#     def sendNew(self, cmd,  blind=False, timeout = TIMEOUT):
#         '''
#         Send a command over the connection. It will login if necessary
#         The login turns echo off. This makes it much easier to parse results. Close will turn echo back on again
#         :param cmd: The shell command to execute
#         :param blind: If should send without waiting for result. Must be used for poweroff
#         :return The response from the device. None in case of error
#         '''
#         if not self.doLogin():
#             print "error could not login"
#             return None
#         try:
#             self.tty.flush()
#             print "before expect eof"
#             self.tty.expect(pexpect.EOF) #Ignore anything currently in stream; move to the end
#             print("after expect eof sending:" + cmd)
#             self.tty.sendline(cmd) #send command to remote
#             time.sleep(4)
#             if (blind): #if don't care about the result. For example, poweroff
#                 return None
#             self._expect(COMMAND_PROMPT_REGEX) #Now _expect the a command prompt after execution
#             result = self.tty.before #everything up to the command prompt is our result
#             result = result.rstrip("\r\n") #in most cases there will be a new line. Only if the return is blank will it be empty
#             return result
#         except Exception, e: # This will happen if the command is invalid on the remote. 
#             serialLog.exception(e)
#             return None
#         finally:
#             self.tty.sendline("") # for next time's login check, send a blank to get a command prompt
            
        
    def send(self, cmd,  blind=False, timeout = TIMEOUT):
        '''
        Send a command over the connection. It will login if necessary
        :param cmd: The shell command to execute
        :param blind: If should send without waiting for result. Must be used for poweroff
        :return The response from the device. None in case of error
        '''
        if not self.loggedIn:
            if not self.doLogin():
                print "error could not login"
                return None

        try:
#             self.tty.read() # read everything currently in buffer
            self.tty.expect(pexpect.EOF,timeout=1)
            self.tty.sendline(cmd) #send command to remote
            if (blind): #if don't care about the result. For example, poweroff
                return None
            commandRegex = re.compile(re.escape(cmd +"\r\n")) #regex to strip off the command just issued
            bf1 = self._expect(commandRegex) # if this is ever hanging, check to see the line length isn't too long!
            result = self._expect(COMMAND_PROMPT_REGEX, timeout=TIMEOUT) #Now _expect the newline and command prompt
            result = result.rstrip("\r\n") #in most cases there will be a new line. Only if the return is blank will it be empty
            return result
        except Exception, e: # This will happen if the command is invalid on the remote. 
            serialLog.exception(e)
            return None

#     def sendwed(self, cmd,  blind=False, timeout = TIMEOUT):
#         '''
#         Send a command over the connection. It will login if necessary
#         :param cmd: The shell command to execute
#         :param blind: If should send without waiting for result. Must be used for poweroff
#         :return The response from the device. None in case of error
#         '''
# #         if not self.loggedIn:
#         time.sleep(.6)
#         if not self.doLogin():
#             print "error could not login"
#             return None
# 
#         try:
# #             self.tty.read() # read everything currently in buffer
#             
#             self.tty.sendline(cmd) #send command to remote
#             if (blind): #if don't care about the result. For example, poweroff
#                 return None
#             commandRegex = re.compile(re.escape(cmd +"\r\n")) #regex to strip off the command just issued
#             print self.tty.before
#             self.__expect(commandRegex) # if this is ever hanging, check to see the line length isn't too long!
#             time.sleep(.5)
#             print self.tty.before
#             self.__expect(COMMAND_PROMPT_REGEX) #Now __expect the newline and command prompt
#             print self.tty.before
# 
#             result = self.tty.before #everything up to the newline and command prompt is our result
#             result = result.rstrip("\r\n") #in most cases there will be a new line. Only if the return is blank will it be empty
#             time.sleep(.6)
#             self.tty.sendline("") #For next time, we want to have a prompt ready
#             return result
#         except Exception, e: # This will happen if the command is invalid on the remote. 
#             serialLog.exception(e)
#             return None

#     def send(self, cmd,  blind=False, timeout = TIMEOUT):
#         '''
#         Send a command over the connection. It will login if necessary
#         :param cmd: The shell command to execute
#         :param blind: If should send without waiting for result. Must be used for poweroff
#         :return The response from the device. None in case of error
#         '''
#         if not self.doLogin():
#             print "error could not login"
#             return None
#         try:
# #             self.tty.expect(pexpect.EOF) #Ignore anything currently in stream; move to the end
#             cmd = cmd + " ; echo " + COMMAND_DELIMETER + ""
#             self.tty.sendline(cmd) #send command to remote
#             if (blind): #if don't care about the result. For example, poweroff
#                 return None
#  
#             self.__expect(DELIMETER_NEW_LINE_REGEX, expectTimeout=timeout) #First, expect that the command is echoed back to us. We're not interested in it
#             time.sleep(1)
#             self.__expect(DELIMITER_NEW_LINE_COMMAND_PROMPT_REGEX, exact=False) #Now __expect the newline and command prompt
# #             self.__expect(DELIMETER_NEW_LINE_REGEX, exact=False) #Now __expect the newline and command prompt
#             result = self.tty.before #everything up to the newline and command prompt is our result
#             result = result.rstrip("\r\n") #in most cases there will be a new line. Only if the return is blank will it be empty
#             self.tty.sendline("") #For next time, we want to have a prompt ready
#             return result
#         except Exception, e: # This will happen if the command is invalid on the remote. 
#             log.exception(e)
#             return None

#     def sendOld(self, cmd,  blind=False, timeout = TIMEOUT):
#         '''
#         Send a command over the connection. It will login if necessary
#         :param cmd: The shell command to execute
#         :param blind: If should send without waiting for result. Must be used for poweroff
#         :return The response from the device. None in case of error
#         '''
#         delimiter = "END_COMMAND" # careful not to put any special REGEX chars in this string
#         if not self.doLogin():
#             print "error could not login"
#             return None
#         try:
#             if delimiter:
#                 cmd = cmd + " && echo " + delimiter + ""
#             self.tty.sendline(cmd) #send command to remote
#             if (blind): #if don't care about the result. For example, poweroff
#                 return None
# 
#             self.__expect(delimiter+"\r\n", expectTimeout=timeout) #First, expect that the command is echoed back to us. We're not interested in it
#             if delimiter:
#                 self.__expect("" + delimiter + "\r\n" + COMMAND_PROMPT_REGEX, exact=False) #Now __expect the newline and command prompt
#             else:      
#                 self.__expect("\r\n" + COMMAND_PROMPT_REGEX) #Now __expect the newline and command prompt
#             result = self.tty.before #everything up to the newline and command prompt is our result
#             result = result.rstrip("\r\n") #in most cases there will be a new line. Only if the return is blank will it be empty
#             self.tty.sendline("") #For next time, we want to have a prompt ready
#             return result
#         except Exception, e: # This will happen if the command is invalid on the remote. 
#             log.exception(e)
#             return None


    def _expect(self,findString , timeout=TIMEOUT, exact = False):

        index = 0
        start = time.clock()
        end = start + timeout
        step = .1
        
        while index == 0:
            if time.clock() > end: #this timeout behavior isn't really coret since the _expect below has its own timeout
                return None
            time.sleep(step)
            if exact:
                index = self.tty.expect_exact([pexpect.EOF, findString],timeout=timeout) 
            else:
                index = self.tty.expect_list([pexpect.EOF, findString],timeout=timeout) 
        return self.tty.before
            
           
    def close(self):
        '''
        Close the connection. Call when you are done. Also gets called if EOF found
        '''
        self.loggedIn = False
        if self.tty:
#             self.tty.sendline("stty -echo") #turn echo back on
            self.tty.close()
        self.tty = None



# Example to test with
def main():
    ser = SerialConnection()
#     zzz =  ser.send("ls -l")
#     print zzz
    zzz = ser.send ("ls -l")
    print zzz
    zzz =  ser.send("sleep 4")
    print zzz
    zzz = ser.send ("cat asdf")
    print zzz
    
    zzz = ser.send ("ls -l")
    print zzz
    print "done"
#         print ser.send("ps -x")
#         print ser.send("sleep 12; echo hi; ",timeout=1) 
#         ser.send("poweroff",blind=True)
    ser.close()

if __name__ == "__main__":
  exit(main())
#!/usr/bin/env python

#Taken and slightly modified from from: http://stackoverflow.com/questions/3362600/how-to-send-email-attachments-with-python
import smtplib
import glob
import os
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email import Encoders
from email import MIMEText

SMTP_SERVER = 'smtp-mail.outlook.com'
SUBJECT = "logs"
EMAIL_FROM = "ntc_chip_log@outlook.com"
# EMAIL_TO = ["ntc_chip_log@qq.com","howie@nextthing.co"]
EMAIL_TO = ["ntc_chip_log@outlook.com","productionlogs@nextthing.co"]
TEXT="Latest Logs"
SMTP_LOGIN = "ntc_chip_log@outlook.com"
SMTP_PORT = 587
SMTP_PW = "qaWS12!@"
ATTACHMENT_PATH = os.path.expanduser('~')
ATTACHMENT_PATH2 = os.path.expanduser('~') + "/Desktop/CHIP-flasher/flasher"
ATTACHMENT_PATH3 = "/home/debian/Desktop/CHIP-flasher/flasher"
ATTACHMENT_WILDCARD = '*.db'

class LogMailer():
    '''
    This will send log files on the machine to the EMAIL_TO addresses above
    '''
    def __init__(self, send_from=EMAIL_FROM,send_to=EMAIL_TO,subject=SUBJECT,text=TEXT,path=ATTACHMENT_PATH,wildcard=ATTACHMENT_WILDCARD):
        self.subject = subject
        self.send_from = send_from
        self.send_to = send_to
        self.text = text
        self.files = path+"/"+wildcard
        self.files2 = ATTACHMENT_PATH2+"/"+wildcard
        self.files3 = ATTACHMENT_PATH3+"/"+wildcard

    def send(self, server=SMTP_SERVER):

        msg = MIMEMultipart()
        msg['Subject'] = self.subject
        msg['From'] = self.send_from
        msg['To'] = ', '.join(self.send_to)

        files = glob.glob(self.files)
        if files is None or len(files) == 0:
            files = glob.glob(self.files2)
            if files is None or len(files) == 0:
                files = glob.glob(self.files3)

        for filename in files:
            part = MIMEBase('application', "octet-stream")
            part.set_payload(open(filename, "rb").read())
            Encoders.encode_base64(part)
            attachmentName = filename.split('/')[-1] #get last element
            part.add_header('Content-Disposition', 'attachment; filename=' +attachmentName)
            msg.attach(part)
        try:
            server = smtplib.SMTP(SMTP_SERVER,SMTP_PORT)
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SMTP_LOGIN,SMTP_PW)
            server.sendmail(self.send_from, self.send_to, msg.as_string())
            server.close()
        except Exception,e:
            print e

def main():
    mailer = LogMailer()
    mailer.send()

#------------------------------------------------------------------
if __name__ == "__main__":
#------------------------------------------------------------------
  exit( main() )





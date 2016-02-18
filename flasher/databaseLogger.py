import sqlite3 as sql
import sys
import time
import socket

from subprocess import Popen
from collections import OrderedDict
# from flasher import Flasher
from config import *
from runState import RunState
from datetime import datetime, date

get_class = lambda x: globals()[x]

class DatabaseLogger():
    COMMON_COLUMNS = [
        ['chipId','TEXT'], #id of the CHIP from a barcode/QR code on the chip itself
        ['timestamp', 'TIMESTAMP'],   #time when test finished
        ['result', 'INTEGER'], # 1 for pass, 0 for fail
        ['error', 'INTEGER'],  #error code
        ['elapsedTime', 'INTEGER'], #how long it took in seconds
        ['port', 'TEXT'], #the name (number) of the port
        ['computer', 'TEXT'], #hostname
        ['runName','TEXT'] #RUN_NAME in the config file
    ]

    TODAY = " strftime('%Y-%m-%d', timestamp) == strftime('%Y-%m-%d', datetime('now','localtime')) "

    def computeAndFormatStats(self,queries):
        return self.formatStats(self.computeStats(queries))

    def computeStats(self,queries):
        dict = OrderedDict()
        try:
            for query in queries:
                self.con.row_factory = sql.Row
                cur = self.con.cursor()
                cur.execute(query)
    #             group = 'group by' in query
                while True:
                    row = cur.fetchone()
                    if not row:
                        break
    #                 print "row len " + str(len(row))
                    for i in range(0,len(row)):
                        field = row.keys()[i]
                        value = row[i]
                        if '_key' in field: #if this is a key field, meaning values in a sub dict
                            keyField = field.split('_')[0] #remove the suffix
                            valField = keyField +"_val" #find corresponding value field
                            valFieldValue = row[row.keys().index(valField)] #get the value of the value field
                            if not keyField in dict: #if no dict yet
                                dict[keyField] = OrderedDict()
                            dict[keyField][value] = valFieldValue
                        elif not '_val' in field:
                            dict[row.keys()[i]] = row[i]
        except Exception,e:
            print e
        return dict

    def formatStats(self,stats,level=0):
        formatted = ""
        for key,val in stats.iteritems():
            formatted  = formatted + "   " * level #indent
#             print str(val) + "\n"
            if isinstance(val, dict):
                formatted = formatted + str(key) + ":\n"
                formatted = formatted + self.formatStats(val,level+1) #recursive call
            else:
                formatted = formatted + str(key) + ": " + str(val) + "\n"
        return formatted

    def _fileName(self):
        return self.hostName + "_" + LOG_DB

    def launchSqlitebrowser(self):
        try:
            Popen( ["sqlitebrowser",self._fileName()]) #spawns
        except Exception, e:
            print e

    def __init__( self, **kwargs ):
        self.con = None
        self.hostName = socket.gethostname()
        if 'LOG_DB' in globals():
            try:
                self.con = sql.connect(self._fileName(),detect_types=sql.PARSE_DECLTYPES)
            except Exception,e:
                print e

    def __del__(self):
        if self.con:
            self.con.close()

    def _formattedColumns(self,suiteClass):
        cols = list(self.COMMON_COLUMNS) #copy common ones
        if hasattr(suiteClass,'statsTableColumns'):
            cols.extend(suiteClass.statsTableColumns())

        formattedColumns = ', '.join(item[0] + ' ' + item[1] for item in cols) #make a comma separated string of space-separated fields
        return formattedColumns

    def _createTableIfNeeded(self,suiteClass):
        create = 'create table if not exists {0} ({1})'.format(suiteClass.statsTableName(), self._formattedColumns(suiteClass))
        try:
            self.con.execute(create)
            self.con.commit()
        except Exception,e:
            print e


    def onUpdateStateInfo(self, info):
        '''
        Observer callback from main thread. See Controller for details on params
        '''
        if not self.con: #no database connection, so ignore
            return
        state = info.get('state')
        if not state in [RunState.PASS_STATE, RunState.FAIL_STATE]: #skip non ending states
            return
        suiteClass = info.get('suiteClass')
        if not suiteClass or not hasattr(suiteClass,'statsTableName'): #ignore if this test doesnt have a db table
            return

        uid = info['uid']
        state = info.get('state')
        errorNumber = info.get('errorNumber')
        returnValues = info.get('returnValues')
        elapsedTime = info.get('elapsedTime')
        chipId = info.get('chipId')
        self._createTableIfNeeded(suiteClass)
        fields = []
        for field in self.COMMON_COLUMNS:
            fields.append(field[0])
        values = ["'" + str(chipId) + "'", #chipId
                  "'" + str(datetime.fromtimestamp(time.time())) + "'", #timestamp
                  '1' if state == RunState.PASS_STATE else '0', #result
                  str(errorNumber), #error
                  str(elapsedTime), #elapsed
                  "'" + str(uid) + "'", #port
                  "'" + self.hostName + "'", #computer
                  "'" + RUN_NAME + "'"
                ]
        #now add in any fields and values from the dictionary for the specific test
        if hasattr(suiteClass,'statsTableColumns'):
            for col in suiteClass.statsTableColumns():
                fieldName = col[0]
                fields.append(fieldName)
                value = returnValues.get(fieldName)
                if value is None:
                    value = col[2] #use default
                if col[1] == "TEXT":
                    value = "'" + value + "'"
                values.append(str(value)) #look up the field in the dictionary

#         print fields
#         print values

        query = 'INSERT INTO {0} ({1}) VALUES ({2})'.format(suiteClass.statsTableName(),','.join(fields),','.join(values))
#         print query
        try:
            self.con.execute(query)
            self.con.commit()
        except Exception, e:
            print e




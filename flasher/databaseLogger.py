'''
Created on Mar 15, 2017

@author: howie

This module interacts with a backing sqlite3 database. It's used to keep track of flashing stats for each device. 
There is one row for each device. The PK is the serial number
'''
import sqlite3 as sql
import time
import socket

from subprocess import Popen
from collections import OrderedDict
from config import *
from runState import RunState
from datetime import datetime
from chp_flash import ChpFlash
from pydispatch import dispatcher
from chp_controller import PROGRESS_UPDATE_SIGNAL
import itertools
get_class = lambda x: globals()[x] # A shortcut to serach for a class by name

class DatabaseLogger():
    '''
    This class (should be singleton) is used to interact with the database
    '''
    
    #columns common to all tables (hwtest and flashing)
    COMMON_COLUMNS = [
        ['chipId','TEXT','PRIMARY KEY'], #id of the CHIP from a barcode/QR code on the chip itself
        ['timestamp', 'TIMESTAMP'],   #time when test finished
        ['result', 'INTEGER'], # 1 for pass, 0 for fail
        ['error', 'INTEGER'],  #error code
        ['attempts', 'INTEGER'],  #how many tries
        ['elapsedTime', 'INTEGER'], #how long it took in seconds
        ['port', 'TEXT'], #the name (number) of the port
        ['computer', 'TEXT'], #hostname
        ['runName','TEXT'] #RUN_NAME in the config file
    ]

    TODAY = " strftime('%Y-%m-%d', timestamp) == strftime('%Y-%m-%d', datetime('now','localtime')) "
    
    def __init__( self, **kwargs ):
        '''
        Constructor
        '''
        self.con = None
        self.hostName = socket.gethostname()
        dispatcher.connect(self.onUpdateStateInfo.__get__(self,DatabaseLogger), signal = PROGRESS_UPDATE_SIGNAL, sender=dispatcher.Any) #subscribe to updates

        if 'LOG_DB' in globals():
            try:
                self.con = sql.connect(self._fileName(),detect_types=sql.PARSE_DECLTYPES)
            except Exception,e:
                print e

    def computeAndFormatStats(self,queries):
        '''
        Helper function
        :param queries:
        '''
        return self.formatStats(self.computeStats(queries))

    def computeStats(self,queries):
        '''
        Go through the queries that are requested and execute the on the database sotring results in a dict
        :param queries:
        '''
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
        '''
        Temporary solution to format the stats
        :param stats:
        :param level:
        '''
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
        '''
        Generate a name for the stats sqlite3 file
        '''
        return self.hostName + "_" + LOG_DB

    def launchSqlitebrowser(self):
        '''
        Spawn a process which runs the sqlitebrowser tool on the file
        '''
        try:
            Popen( ["sqlitebrowser",self._fileName()]) #spawns
        except Exception, e:
            print e


    def __del__(self):
        '''
        Destructor. Clean up connection
        '''
        if self.con:
            self.con.close()

    def _formattedColumns(self,suiteClass):
        '''
        Helper function to generate the SQL for a query
        :param suiteClass:
        '''
        cols = list(self.COMMON_COLUMNS) #copy common ones
        if hasattr(suiteClass,'statsTableColumns'):
            cols.extend(suiteClass.statsTableColumns())

        formattedColumns = ', '.join(' '.join(item) for item in cols) #make a comma separated string of space-separated fields
        return formattedColumns

    def _createTableIfNeeded(self,suiteClass):
        '''
        Create the table if it doesn't exist yet
        :param suiteClass: e.g. ChpFlash
        '''
        create = 'create table if not exists {0} ({1})'.format(suiteClass.statsTableName(), self._formattedColumns(suiteClass))
        try:
            self.con.execute(create)
            self.con.commit()
        except Exception,e:
            print e
    
    def find(self, chipId):
        '''
        Find a CHIP in the database
        :param chipId: serial number
        '''
        try:
            findQuery = "SELECT * FROM {0} WHERE chipId='{1}'".format(ChpFlash.statsTableName(),chipId)
            self.con.row_factory = sql.Row
            cur = self.con.cursor()
            cur.execute(findQuery)
            row = cur.fetchone()
            if row:
                rowDict = dict(itertools.izip(row.keys(), row))
                return rowDict
        except Exception,e:
            print "No database. Will create it",e
        return None


    def onUpdateStateInfo(self, info):
        '''
        Respond to device state changes, only caring about PASS and FAIL states
        Log results to database
        :param info:
        '''
        '''
        Observer callback from main
        '''
        if not self.con: #no database connection, so ignore
            return
        state = info.get('runState')
        if not state in [RunState.PASS_STATE, RunState.FAIL_STATE]: #skip non ending states
            return
        suiteClass = ChpFlash
        if not suiteClass or not hasattr(suiteClass,'statsTableName'): #ignore if this test doesnt have a db table
            return

        uid = info['uid']
        if not uid: #don't log nulls
            return
        state = info.get('runState')
        errorNumber = info.get('errorNumber') or 0
        returnValues = info.get('returnValues')
        elapsedTime = info.get('elapsedTime')
        chipId = info.get('chipId')
            
        self._createTableIfNeeded(suiteClass)
        fields = []
        for field in self.COMMON_COLUMNS:
            fields.append(field[0])

        attempts = 0
        row = self.find(chipId)
        if row:
            attempts = int(row['attempts'])
        attempts += 1

        values = ["'" + str(chipId) + "'", #chipId
                  "'" + str(datetime.fromtimestamp(time.time())) + "'", #timestamp
                  '1' if state == RunState.PASS_STATE else '0', #result
                  str(errorNumber), #error
                  str(attempts),
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

        query = 'INSERT OR REPLACE INTO {0} ({1}) VALUES ({2})'.format(suiteClass.statsTableName(),','.join(fields),','.join(values))
        try:
            self.con.execute(query)
            self.con.commit()
        except Exception, e:
            print e




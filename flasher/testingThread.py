import threading
from kivy.clock import Clock
from progress import Progress
import unittest
from observable_test import *
from ui_strings import *
from guiContants import *


class TestResult:
    def __init__(self):
        pass
    
    success = None
    resultText = None
    
class TestingThread(threading.Thread):
    def __init__(self,  suite, deviceDescriptor,count, mutexes, updateQueue, testResult):
        '''
        I am intentionally not passing in the parent to prevent abuse of threads
        :param suite: The unittest suite to run
        :param deviceDescriptor: 
        :param count: counter of current number of runs. used for logs
        :param mutexes: Dictionary of mutexes
        :param updateQueue: queue to manage Kivy updates
        :param testResult: The result of the tests will be stored here for the main thread to use
        '''
        threading.Thread.__init__(self)
        self.suite = suite
        self.deviceDescriptor = deviceDescriptor
        self.count = count #used for traces for how many runs
        self.mutexes =  mutexes
        self.updateQueue = updateQueue
        self.testResult = testResult
        self.uid = deviceDescriptor.uid
        self.testCaseAttributes = {'deviceDescriptor': deviceDescriptor} #such as for the flasher to get the port. Passed along to the unittest
        self.totalProgressSeconds = sum( progressForTest(testCase) for testCase in suite)
        self.output = "" 
        self.currentStateName = ""
        self.currentStateFailMessage = None
        self.event = None # event gets set when a prompt goes up
            
    def run(self):
        '''
        Entry point for the thread
        '''
        stateInfoCallback = self.onStateChange.__get__(self, TestingThread) #Register for state changes from the unittest suite - meaning when a test case is about to run or has run
        progressCallback = self._onProgressChange.__get__(self,TestingThread) #this progress is not used right now, but can be.
        
        #Decorate all of the tests to add observers to them
        for testCase in self.suite:
            decorateTest(testCase, stateInfoObservers = [stateInfoCallback], progressObservers = [progressCallback], attributes = self.testCaseAttributes ) #Decorate the test cases to add the callback observer and logging above

        #RUN THE TESTS!
        result = unittest.TextTestRunner(verbosity=1, failfast=True).run(self.suite) # This runs the whole suite of tests. For now, using TextTestRunner
        
        #Process test results. self.testResult is populated. The calling thread can use it if it wants
        self.testResult.success = len(result.errors) + len(result.failures) == 0 # Any errors?
        if self.testResult.success:
            state = PASS_STATE
            stateLabel = PASS_TEXT
            self.testResult.resultText = "Passed"
        else:
            self.testResult.resultText = self.currentStateName + "Failed"
            state = FAIL_STATE
            if self.currentStateFailMessage:
                stateLabel = self.currentStateFailMessage
            else:
                stateLabel = FAIL_TEXT
        self.output += self.testResult.resultText
        
        #update the UI
        self._updateStateInfo({'state': state, 'stateLabel': stateLabel, 'output': self.output})
        #the main thread can access the result through testResult

    def processButtonClick(self):
        '''
        The main thread sends along button clicks so the thread can wake up if its waiting for a prompt
        '''
        if self.event: #this would be set before showing a prompt
            self.event.set()
            self.event = None
        
    def onStateChange(self,stateInfo):
        '''
        This method is an observer called from the decorator in obervable_test.
        It is called both before and after the actual test is run
        
        :param stateInfo: See observable_test for what's here
        '''
        
        #Get info about the test case and if we are before or after
        testCase = stateInfo['testCase']
        label = stateInfo['label']
        englishName = label.split('\n')[0] #For output window
        self.currentStateName = englishName
        before = stateInfo['when']== "before"

        #get any decorators for the test case        
        progressSeconds =  progressForTest(testCase) # @progress
        timeout =  timeoutForTest(testCase) # @timeout - this is not hooked in yet
        mutex = mutexForTest(testCase) # @mutex
        self.currentStateFailMessage = failMessageForTest(testCase) # a fail message to show
        
        if before:
            #initialize pre-test stuff
            self.output += (str(self.count) + ": BEFORE: " + englishName + " device: "+ self.deviceDescriptor.uid + "\n")
            self._updateStateInfo({'state': ACTIVE_STATE, 'labelText': label, 'output': self.output, 'progress': 0})
            testCase.output=""
            self.progress = None
            self._showPromptIfAny(promptBeforeForTest(testCase)) # @promptBefore
            
            if mutex: #if this test needs a mutex as indicated in the test suite
                if not mutex in self.mutexes:
                    self.mutexes[mutex] = threading.Lock() #make a new one. This should only get called once per mutex, per app run
                lock = self.mutexes[mutex] #get the lock
                self._updateStateInfo({'state': PAUSED_STATE, 'stateLabel': PAUSED_TEXT})
                lock.acquire() #Wait, if necessary, until the lock is free and then grab it
            
            # We've got the lock now, so now indicate we are active
            self._updateStateInfo({'state': ACTIVE_STATE, 'stateLabel': RUNNING_TEXT})
            if progressSeconds: #progress bar should be shown
                self.progress = Progress(progressObservers = [self._onProgressChange.__get__(self,TestingThread)], finish=progressSeconds, timeout = timeout )
            
            
        else: #AFTER
            self._showPromptIfAny(promptAfterForTest(testCase)) # @promptAfter
            if mutex: # @mutex is an annotation defined in observable_test
                self.mutexes[mutex].release() #free up the lock
            if progressSeconds:
                self.progress.stopListening() #no longer want to get progress
                
            #update the output from the test case
            self.output += testCase.output
            self.output += (str(self.count) + ": AFTER: " + englishName + " device: "+ str(self.uid) + " time: " + str(stateInfo['executionTime']) + "\n")
            self._updateStateInfo({'state': PASSIVE_STATE, 'output': self.output})

######################################################################################################################################
# Privates
######################################################################################################################################
    def _showPromptIfAny(self, prompt):
        if prompt: #this can be before and/or after
            self.event = threading.Event() #create an event that will be used to wake up the thread via processButtonClick
            self._updateStateInfo({'prompt': prompt, 'state': PROMPT_STATE})
            self.event.wait() #now wait for a call to processButtonClick sent main mainthread
            self._updateStateInfo({'state': ACTIVE_STATE, 'labelText': label}) #after resume, now active. also reset label because prompt used it

    def _updateStateInfo(self,info):
        '''
        Queue a dictionary of GUI changes which Kivy will process in its main thread
        :param info: dictionary of values to change. See TestSuiteGUIApp._udpateStateInfo for possible values
        '''
        info['uid'] = self.uid
        # maybe the state value, if present, should be updated here immediately? Currently the main thread will do it
        self.updateQueue.put(info)
    
    def _onProgressChange(self,progress):
        '''
        Callback for updating progress bar
        :param progress:
        '''
        self._updateStateInfo({'progress': progress})

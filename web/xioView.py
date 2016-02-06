import threading
import time
from libsoc import GPIO
from libsoc import DIRECTION_OUTPUT
from flasher import RunState

class XioView:
    BLINKS = {RunState.DISCONNECTED_STATE:[0,.1],
              RunState.PASSIVE_STATE: [2,2],
              RunState.ACTIVE_STATE: [.5,.5],
              RunState.PAUSED_STATE:[.01,.01],
              RunState.PROMPT_STATE:[.2,1],
              RunState.PASS_STATE: [100,0],
              RunState.FAIL_STATE: [1,1]}

    def __init__( self, **kwargs ):
        self._xios = [0,1, 2,4,6,7]
        self._xioMap = {}
        self._blinkThreads = {}
        '''
        The view part of the MVC. note that some values are passed in the kwargs dict. See below
        Basically, this method will create and layout the gui's widgets
        '''
        count = 0;
        self.deviceDescriptors = kwargs['deviceDescriptors']
        self.hubs = kwargs['hubs']
        for i,hub in enumerate(self.hubs): #go through the hubs
            for key, deviceDescriptor in self.deviceDescriptors.iteritems(): #now go through devices
                if deviceDescriptor.hub != hub:
                    continue #not on this hub, ignore
                self._xioMap[key] = self._xios[count];
                count = count + 1
                if count >= len(self._xios):
                    break # no more lights!

    def onUpdateStateInfo(self, info):
        '''
        Observer callback from main thread
        :param info:
        '''
        uid = info['uid']
        state = info.get('state')
        if not uid in self._blinkThreads:
            xio = self._xioMap[uid]
            self._blinkThreads[uid] = BlinkThread(xio)
            self._blinkThreads[uid].start()
        self._blinkThreads[uid].setBlinkPattern(XioView.BLINKS[state])
                                           
class BlinkThread(threading.Thread):
    BASE_XIO = 408
    
    def setBlinkPattern(self,blinkPattern):
        self._blinkPattern = blinkPattern
        
    def xioToDev(self,xio):
        return self.BASE_XIO + xio;

    _stopped = False
    def __init__(self, xioNumber):
        '''
        :param onFor: ms to keep light on
        :param onFor: ms to keep light off
        '''
        self._xio = GPIO(self.xioToDev(xioNumber),DIRECTION_OUTPUT)
        self._xio.open()
        self._xio.set_high() #start off in high (off) state
        self._blinkPattern = [0,.1]
        threading.Thread.__init__(self)
        
    def stop(self):
        self._stopped = True
        
    def run(self):
        while True:
            state = True 
            for blink in self._blinkPattern:
                if self._stopped: #detect stop here too
                    break
                if state:
                    self._xio.set_low() #low is on
                else:
                    self._xio.set_high() # high is off
                state = not state #toggle 
                time.sleep(blink)

from kivy.clock import Clock
class Progress(object):
    '''
    Small class to keep track of progress and update progress observers on change
    '''
    def __init__(self, progressObservers = [], timeoutObservers = [], start = 0.0, finish=1.0, timeout=None):
        self.progressObservers = progressObservers
        self.timeoutObservers = timeoutObservers
        self.start = start
        self.finish = finish
        self.current = start
        self.timeout = timeout
        self.timedOut = False
        Clock.schedule_interval(self.addProgress.__get__(self,Progress), 1 )
    
    def stopListening(self):
        Clock.unschedule(self.addProgress.__get__(self,Progress))

#     def __del__(self):
#         Clock.unschedule(self.addProgress.__get__(self,Progress))
        
    def addProgress(self,change):
        self.setProgress(self.current + change)

    def setProgress(self, value):
        self.current = value
        progress = self.getProgress()
        [observer(progress) for observer in self.progressObservers]
        if self.timeout:
            if value >= self.timeout:
                self.timedOut = True
                [observer() for observer in self.timeoutObservers]
                

        
    def getProgress(self):
        return self.current / self.finish


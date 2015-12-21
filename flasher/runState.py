#states

class RunState:
    '''
    Helper class to keep track of the correspondance between a device and its state info
    '''
    DISCONNECTED_STATE = -1
    PASSIVE_STATE = 0
    ACTIVE_STATE = 1
    PAUSED_STATE = 2
    PROMPT_STATE = 3
    PASS_STATE = 4
    FAIL_STATE = 5
    IDLE_STATE = 6

    def __init__(self, uid):
        self.uid = uid
        self.state = self.PASSIVE_STATE
        self.output = " "
        
    def isActive(self):
        return self.state == self.ACTIVE_STATE
    
    def isIdle(self):
        return self.state in [self.PASSIVE_STATE, self.PAUSED_STATE, self.PROMPT_STATE, self.IDLE_STATE]
    
    def isDone(self):
        return self.state in [self.PASS_STATE, self.FAIL_STATE]
        

# -*- coding: utf-8 -*-

from functools import wraps
import time

def observeTest(func):
    '''
    Decorator for unit tests. This will wrap the run function to add timings and also 
    to call observers both before and after the run function is called. 
    Observers are called with a dict containing information about the test itself:
    when: ["before" | "after"]
    method: The name of the python function used in the test
    label: A more descriptive label for this test, perhaps to show in a GUI
    testCase: The object for which the method is a member. 
    
    Additionally, decorator attributes are copied into the instance method
    
    :param func: The test function to get decorated
    '''
    @wraps(func)
    def wrapper(*args, **kwargs):
        instance = func.im_self  # the test case object
        methodName = instance._testMethodName  # the name of the bound testing func

        '''    
        Now copy over  decorator-populated attrubtes from the unbound func to the instance method.
        Basically, the issue is that Python 2.7 decorators (e.g. @myDecorator) are executed before any instances are instantiated
        As a result, the instance methods (bound to their object) do not have the unbound version's attributes
        '''
        unboundFunc = instance.__class__.__dict__[methodName]  # get the unbound function with this name to copy its decoratored values
        if not hasattr(instance, "_attributes"):  # if no existing attributes map
            instance._attributes = {}  # make a new one
        instance._attributes.update(unboundFunc._attributes)  # this will copy attributes from the unbound func into the bound method's attributes
        if 'label' in instance._attributes:
            label = instance._attributes['label']  # use the label that was set in the @label
        else:
            label = methodName  # in case not found, use the method's name for the label
            
        # Populate the stateInfo for observer callbacks            
        stateInfo = {"when":"before", "method":methodName, "label": label, "testCase": instance }
        
        start = time.time()  # let's keep track of execution time
        [observer(stateInfo) for observer in instance.stateInfoObservers]  # tell observers test is about to run
        try:
            r = func(*args, **kwargs)  # execute the test
        except Exception, e:
            raise(e) # the finally block below will close out timer and notify observers
        finally:
            end = time.time() 
            stateInfo['executionTime'] = end - start  # is stateInfo the right place for this?
            stateInfo['when'] = "after"  # The test is over, so  
            [observer(stateInfo) for observer in instance.stateInfoObservers]  # notify test done
        return r 
    return wrapper

# 
def _addAttribute(meth, att, name):
    '''
    Convenience method for the specific decorators below
    :param meth:
    :param att:
    :param name:
    '''
    if not hasattr(meth, "_attributes"):
        meth._attributes = {}
    meth._attributes[att] = name
    return meth
          
def label(text):
    '''
    @label decorator
    :param value: descriptive text to display for this test, such as in a GUI
    '''
    def method_call(method):
        return _addAttribute(method, "label", text)
    return method_call
    
        
def progress(seconds):
    '''
    @progress decorator
    :param seconds: number of seconds on the animated progress bar
    '''
    def method_call(method):
        return _addAttribute(method, "progress", seconds)
    return method_call

def promptBefore(text):
    '''
    @label decorator
    :param value: user should be prompted for input (click) with this text before test execution
    '''
    def method_call(method):
        return _addAttribute(method, "promptBefore", text)
    return method_call
    
def promptAfter(text):
    '''
    @label decorator
    :param value: user should be prompted for input (click) with this text after test execution
    '''
    def method_call(method):
        return _addAttribute(method, "promptAfter", text)
    return method_call

def timeout(seconds):
    '''
    @timeout decorator
    :param seconds: number of seconds a test can run before timeout
    '''
    def method_call(method):
        return _addAttribute(method, "timeout", seconds)
    return method_call

def decorateTest(test, stateInfoObservers=None, progressObservers=None):  
    '''
    Decorate a test to use the observeTest decorator above, passing along observers
    :param test:
    :param stateInfoObservers:
    :param progressObservers:
    '''
    test.run = observeTest(test.run) # apply the decorator
    test.stateInfoObservers = []
    test.stateInfoObservers.extend(stateInfoObservers)
    test.progressObservers = []
    test.progressObservers.extend(progressObservers)
    
    
def _decoratedAttribute(test, name):
    '''
    Helper function for methods below to extract an attribute of a test's method
    :param test:
    :param name:
    '''
    funcAttributes =  test.__class__.__dict__[test._testMethodName]
    if not hasattr(funcAttributes,'_attributes'):
        funcAttributes._attributes = {}
    attributes =funcAttributes._attributes  # get the decorated attributes for this test
    if name in attributes:
        return attributes[name]
    return None
    
    
def labelForTest(test):
    '''
    Get the @label
    Note that a None value for the label indicates that the test is run 'quietly', without a label showing up
    :param test:
    '''
    return _decoratedAttribute(test, 'label')

def promptBeforeForTest(test):
    '''
    Get the @promptBefore
    :param test:
    '''
    return _decoratedAttribute(test, 'promptBefore')

def promptAfterForTest(test):
    '''
    Get the @promptAfter
    :param test:
    '''
    return _decoratedAttribute(test, 'promptAfter')

def timeoutForTest(test):
    '''
    Get the @timeout
    :param test:
    '''
    return _decoratedAttribute(test, 'timeout')

def progressForTest(test):
    '''
    Get the @progress
    :param test:
    '''
    return _decoratedAttribute(test, 'progress')

def methodForTest(test):
    '''
    Get the method for a test. This can serve as a key with which to refer to this test
    :param test:
    '''
    #TODO this should return a unique value- the pointer ideally
    return test._testMethodName


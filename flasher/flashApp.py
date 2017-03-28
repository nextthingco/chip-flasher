#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys

from config import *

#perform some sanity checks so we can fail fast
if not os.path.exists(CHP_FILE_NAME):
    print "Error! The .chp file specified in config.py could not be found: " + CHP_FILE_NAME
    sys.exit(-1)

if not os.path.exists(UDEV_RULES_FILE):
    print "Error! The udev rules file specified in config.py could not be found: " + UDEV_RULES_FILE
    sys.exit(-1)
    
#Need this to get right font
# wget http://ftp.us.debian.org/debian/pool/main/f/fonts-android/fonts-droid_4.4.4r2-6_all.deb
# dpkg -i fonts*.deb
if os.path.isfile(OSX_FONT):
    FONT_NAME = OSX_FONT
else:
    FONT_NAME = UBUNTU_FONT

if not os.path.exists(FONT_NAME):
    print "Error! The font specified in config.py could not be found: " + FONT_NAME
    sys.exit(-1)
    
import logging
from kivy.logger import Logger
Logger.setLevel(logging.ERROR) #kivy still sends a few logs, but this hides most

from kivy.config import Config
# Config.set('graphics', 'fullscreen', '1')
Config.set('graphics', 'width', '1024')
Config.set('graphics', 'height', '768')
Config.set('graphics', 'window_state', "maximized")
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.progressbar import ProgressBar
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.lang import Builder
from kivy.properties import StringProperty
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.popup import Popup
from kivy.uix.stencilview import StencilView

from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.splitter import Splitter

from runState import RunState
from ui_strings import *
from chp_controller import ChpController, PROGRESS_UPDATE_SIGNAL
from databaseLogger import DatabaseLogger
from pydispatch import dispatcher



class FlashApp(App):
    __slots__ = ('controller', 'kivyUpdateTrigger', 'databaseLogger', 'view', 'stateListeners') #using slots prevents bugs where members are created by accident

    def __init__(self):
        super(FlashApp, self).__init__()
        self.databaseLogger = DatabaseLogger()
        log = Logger

        self.controller = ChpController(CHP_FILE_NAME, self.databaseLogger, log)
        Clock.schedule_interval(lambda x: self.controller.checkForChanges(), 0.1) #the controller must check for changes periodically
        
    def build(self):
        self.controller.createProcesses()
        fileInfo = self.controller.getFileInfo()
        self.view = FlashView(deviceDescriptors=self.controller.deviceDescriptors,
                             hubs=self.controller.hubs, fileInfo=fileInfo,databaseLogger = self.databaseLogger)
        # observe button events if GUI
        self.view.addMainButtonListener(
            self._onMainButton.__get__(self, FlashApp))
        self.view.controller = self.controller
        self.title = "Flashing " + CHP_FILE_NAME
        return self.view

    def _onMainButton(self, button):
        '''
        Handle button clicks on id column as triggers to do something
        :param button:
        '''
        self.controller.onTriggerDevice(button.id)


class BoxStencil(BoxLayout, StencilView):
    pass

class FlashView(BoxLayout):

    def __init__(self, **kwargs):
        '''
        The view part of the MVC. note that some values are passed in the kwargs dict. See below
        Basically, this method will create and layout the gui's widgets
        '''
        super(FlashView, self).__init__(**kwargs)
        self.deviceDescriptors = kwargs['deviceDescriptors']
        self.hubs = kwargs['hubs']
        self.fileInfo = kwargs['fileInfo']
        self.databaseLogger = kwargs['databaseLogger']
        dispatcher.connect(self.onUpdateStateInfo.__get__(self,FlashView), signal = PROGRESS_UPDATE_SIGNAL, sender=dispatcher.Any) #subscribe to updates

        self.widgetsMap = {}
        # the uid of of what's being shown in the output (detail) view to the
        # right of the splitter
        self.outputDetailUid = None
        self.mainButtonListeners = []
        # LAYOUT
        # the right half of the splitter
        outputView = BoxStencil(orientation='vertical')
        self.outputTitle = Label(
            text=" ", font_size=20, color=YELLOW_COLOR, size_hint=(1, .1))
        outputView.add_widget(self.outputTitle)  # add in a title

        self.output = ScrollableLabel()
        outputView.add_widget(self.output)
        buttonGrid = GridLayout(cols=5,size_hint=(1,.15),valign="bottom")
        outputView.add_widget(buttonGrid)

        fileInfoButton = Button(text="File Info")
        buttonGrid.add_widget(fileInfoButton)
        fileInfoButton.bind(on_press=lambda button: self._fileInfo())

        flashStatsButton = Button(text="Flash Stats")
        buttonGrid.add_widget(flashStatsButton)
        flashStatsButton.bind(on_press=lambda button: self._stats("Flasher"))

        browseStatsButton = Button(text="Browse Stats")
        buttonGrid.add_widget(browseStatsButton)
        browseStatsButton.bind(on_press=lambda button: self._browseStats())

        powerButton = Button(text=POWER_OFF_TEXT,font_name=FONT_NAME)
        buttonGrid.add_widget(powerButton)
        powerButton.bind(on_press=lambda button: self._powerOff())

        splitter = Splitter(sizable_from='left', min_size=10,
                            max_size=600, keep_within_parent=True, size_hint=(.01, 1))

        # size the columns appropriately
        # 14.0 / rows #adjust font size according to number of rows
        rowSizeFactor = 4.0
        if not SHOW_STATE:
            rowSizeFactor += 1.5
        if HUBS_IN_COLUMNS:
            hubColumns = len(self.hubs)
        else:
            hubColumns = 1

        if HUBS_IN_COLUMNS:
            rowSizeFactor = rowSizeFactor / hubColumns

        mainButtonWidth = 50 * rowSizeFactor
        hubPanels = GridLayout(cols=hubColumns)

        # Layout the grid for the hubs
        cols = 3
        if not SHOW_STATE:
            cols = cols - 1
        for i, hub in enumerate(self.hubs):  # go through the hubs
            # the spliter is way off to the right
            testingView = GridLayout(cols=cols, size_hint=(.99, 1))
            hubPanels.add_widget(testingView)
            # add these to the py grid view. If we want to have many columns,
            # this would add to a sub grid
            addTo = testingView
            # now go through devices
            for key, deviceDescriptor in self.deviceDescriptors.iteritems():
                if deviceDescriptor.hub != hub:
                    continue  # not on this hub, ignore

                widgets = Widgets()
                self.widgetsMap[key] = widgets

                # The main button
                widgets.button = Button(id=key, text=deviceDescriptor.uid, color=DISCONNECTED_COLOR, font_size=30 * rowSizeFactor,
                                        font_name=FONT_NAME, halign="center", size_hint_x=None, width=mainButtonWidth)
                widgets.button.bind(
                    on_press=self._onClickedMainButton.__get__(self, FlashView))
                addTo.add_widget(widgets.button)

                # The state column
                widgets.stateLabel = Label(id=key, text=WAITING_TEXT, color=DISCONNECTED_COLOR, font_size=13 *
                                           rowSizeFactor, font_name=FONT_NAME, halign="center", size_hint_x=None, width=60 * rowSizeFactor)
                if SHOW_STATE:
                    addTo.add_widget(widgets.stateLabel)

                # The label column kists of both text and a progress bar
                # positioned inside a box layout
                stateBox = BoxLayout(orientation='vertical')
                widgets.label = LabelButton(
                    id=key, text='', color=DISCONNECTED_COLOR, font_size=13 * rowSizeFactor, font_name=FONT_NAME, halign="center")
                # show output window if label clicked
                widgets.label.bind(
                    on_press=self._onShowOutput.__get__(self, FlashView))
                stateBox.add_widget(widgets.label)
                widgets.progress = ProgressBar(
                    id=key, value=0, max=1, halign="center", size_hint=(.9, 1.0 / 15))
                stateBox.add_widget(widgets.progress)
                addTo.add_widget(stateBox)

        splitter.add_widget(outputView)
        self.add_widget(hubPanels)
        self.add_widget(splitter)

    def addMainButtonListener(self, listener):
        '''
        Add an observer to the main button. The Main app will listen to button clicks
        :param listener:
        '''
        self.mainButtonListeners.append(listener)

    # static
    _stateToColor = {RunState.PASSIVE_STATE: PASSIVE_COLOR, RunState.PASS_STATE: SUCCESS_COLOR, RunState.FAIL_STATE: FAIL_COLOR, RunState.PROMPT_STATE: PROMPT_COLOR,
                     RunState.ACTIVE_STATE: ACTIVE_COLOR, RunState.PAUSED_STATE: PAUSED_COLOR, RunState.IDLE_STATE: PASSIVE_COLOR, RunState.DISCONNECTED_STATE: DISCONNECTED_COLOR}

    def onUpdateStateInfo(self, info):
        '''
    info.uid: The port
    info.state: corresponds to the states. e.g. PASSIVE_STATE
    info.stateLabel: Text label for the state, such as RUNNING_TEXT
    info.label: The label for the test case that is being run
    info.progress: number value for progress bar
    info.output: The output for the test case
    info.prompt: Any prompt to show
    '''
        uid = info['uid']
        state = info.get('runState')
        stateLabel = info.get('state')
        label = info.get('stage')
        progress = info.get('progress')
        output = info.get('output')

        widgets = self.widgetsMap[uid]
        
        #checks below explicitly compare to None because empty string and 0 are important values
        if state is not None:
            color = self._stateToColor[state]
            widgets.setColor(color)

        if stateLabel is not None:
            widgets.stateLabel.text = stateLabel

        if label is not None:
            widgets.label.text = label

        if progress is not None: #0 is a real value
            widgets.progress.value = progress

        if output is not None:
            widgets.output = output
            # if the output detail is showing this output, it will be updated
            self._onShowOutput(None, uid)


##########################################################################
# Privates
##########################################################################
    def _onClickedMainButton(self, button):
        '''
        When the button is clicked, notify all listeners
        :param button:
        '''
        for listener in self.mainButtonListeners:
            listener(button)

    def _onShowOutput(self, button, uid=None):
        '''
        Show the output for the currently selected port (by clicking on its label column, not port column
        :param button: this will be the id of the port if invoked through button. Null if called explicitly
        :param uid: Id of the port to show
        '''
        if uid:
            # skip if trying to update output, but parent isnt showing it
            if self.outputDetailUid != uid:
                return
        else:
            uid = button.id
        # signify that we want to show this port now
        self.outputDetailUid = uid
        widgets = self.widgetsMap[uid]
        title = "Port: " + str(uid)
        color = widgets.label.color  # use same color as state
        self._setOutputDetailTitle(title, color)
        self.output.text = widgets.output

    def _setOutputDetailTitle(self, title, color=None):
        '''
        Call to set the title of the output window
        :param title: Title of the
        '''
        self.outputTitle.text = title
        if color:
            self.outputTitle.color = color

    def _stats(self,suiteName):
        queries = self.controller.getStatsQueries(suiteName,self.databaseLogger.TODAY)
        formatted = self.databaseLogger.computeAndFormatStats(queries)
        popup = Popup(title=suiteName + ' stats for today',content=Label(text=formatted),size_hint=(None, None), size=(600, 600))
        popup.open()

    def _fileInfo(self):
        popup = Popup(title='File Info',content=Label(text=self.fileInfo),size_hint=(None, None), size=(600, 600))
        popup.open()

    def _powerOff(self):
        bl = BoxLayout(size_hint=(1, 1))
        bl.add_widget(Label(text=POWER_OFF_TEXT,font_name=FONT_NAME))
        yes = Button(text=YES_TEXT,font_name=FONT_NAME)
        bl.add_widget(yes)
        yes.bind(on_press=lambda button: self.controller.powerOff())

        nope = Button(text=NO_TEXT,font_name=FONT_NAME)
        bl.add_widget(nope)
        nope.bind(on_press=lambda button: popup.dismiss())

        popup = Popup(title="",font_name=FONT_NAME, content=bl,size_hint=(None, None), size=(400, 110),auto_dismiss=False) #kivy wont let me set proper font for title, so i cant get unicode
        popup.open()

    def _browseStats(self):
        self.databaseLogger.launchSqlitebrowser()

class Widgets:
    '''
    Helper class to handle the row widgets
    '''

    def __init__(self):
        self.button = None
        self.stateLabel = None
        self.label = None
        self.progress = None
        self.output = ""  # This is actually the output text for the widget

    def setColor(self, color):
        '''
        Set all widgets in the row to the same color
        :param color:
        '''
        self.color = color
        self.button.color = color
        self.stateLabel.color = color
        self.label.color = color
        self.progress.color = color


class LabelButton(ButtonBehavior, Label):
    '''
    This is a mixin which will add the ability to receive push events from a label. No code needed
    '''
    pass

Builder.load_string('''
<ScrollableLabel>:
    Label:
        size_hint_y: None
        height: self.texture_size[1]
        text_size: self.width, None
        text: root.text
''')



class ScrollableLabel(ScrollView):
    text = StringProperty('')

##########################################################################
if __name__ == '__main__':
    app = FlashApp()
    try:
        app.run()
    except (KeyboardInterrupt, SystemExit):
        app.stop()

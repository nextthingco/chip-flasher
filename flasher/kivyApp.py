# -*- coding: utf-8 -*-
from kivy.config import Config
# Config.set('graphics', 'fullscreen', '1')
Config.set('graphics', 'width', '1024')
Config.set('graphics', 'height', '768')
Config.set('graphics', 'window_state', "maximized")
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.progressbar import ProgressBar
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.core.window import Window
from kivy.uix.behaviors import ButtonBehavior
from kivy.graphics import Color
from kivy.lang import Builder
from logmanager import LogManager
from kivy.properties import StringProperty
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.popup import Popup
from kivy.uix.stencilview import StencilView
from collections import OrderedDict
import collections
import os
import sys

from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.splitter import Splitter

from deviceDescriptor import DeviceDescriptor
from runState import RunState
from config import *
from ui_strings import *
from controller import Controller
from databaseLogger import DatabaseLogger

OSX_FONT = "/Library/Fonts/Arial Unicode.ttf"
UBUNTU_FONT = "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf"
#UBUNTU_FONT = "/usr/share/fonts/truetype/ubuntu-font-family/Ubuntu-B.ttf"
if os.path.isfile(OSX_FONT):
    FONT_NAME = OSX_FONT
else:
    FONT_NAME = UBUNTU_FONT


log = LogManager.get_global_log()


class KivyApp(App):

    def __init__(self, testSuiteName):
        super(KivyApp, self).__init__()
        self.controller = Controller(log, testSuiteName)
        self.kivyUpdateTrigger = Clock.create_trigger(self._onUpdateTrigger.__get__(
            self, KivyApp))  # kivy Trigger that will be set when added to queue
        # this will be called everytime an update is added to the queue
        self.controller.addUpdateQueueListener(self.kivyUpdateTrigger)

    def build(self):
        self.controller.configure()
        # Poll for device changes every second
        Clock.schedule_interval(self._onPollingTick.__get__(self, KivyApp), 1)
        self.databaseLogger = DatabaseLogger()
        self.view = KivyView(orientation='vertical', deviceDescriptors=self.controller.deviceDescriptors,
                             hubs=self.controller.hubs, fileInfo=self.controller.getFileInfo(),databaseLogger = self.databaseLogger)
        # observe button events if GUI
        self.view.addMainButtonListener(
            self._onMainButton.__get__(self, KivyApp))
        self.view.controller = self.controller
        self.controller.addStateListener(lambda info: self.view.onUpdateStateInfo(info))
        self.controller.addStateListener(lambda info: self.databaseLogger.onUpdateStateInfo(info))
        self.title = self.controller.getTitle()
        return self.view

    def on_stop(self):
        '''
        Called from Kivy at end of run
        '''
    #         PersistentData.write()
    #         LogManager.close_all_logs()
        pass

    def _onUpdateTrigger(self, x):
        self.controller.onUpdateTrigger(x)

    def _onPollingTick(self, dt):
        self.controller.onPollingTick(dt)

    def _onMainButton(self, button):
        '''
        Handle button clicks on id column as triggers to do something
        :param button:
        '''
        self.controller.onMainButton(button)

class BoxStencil(BoxLayout, StencilView):
    pass

class KivyView(BoxLayout):

    def __init__(self, **kwargs):
        '''
        The view part of the MVC. note that some values are passed in the kwargs dict. See below
        Basically, this method will create and layout the gui's widgets
        '''
        super(KivyView, self).__init__(**kwargs)
        self.deviceDescriptors = kwargs['deviceDescriptors']
        self.hubs = kwargs['hubs']
        self.fileInfo = kwargs['fileInfo']
        self.databaseLogger = kwargs['databaseLogger']
        self.widgetsMap = {}
        # the uid of of what's being shown in the output (detail) view to the
        # right of the splitter
        self.outputDetailUid = None
        self.mainButtonListeners = []
        self.mainButtons = []
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

        hwStatsButton = Button(text="HW Test Stats")
        buttonGrid.add_widget(hwStatsButton)
        hwStatsButton.bind(on_press=lambda button: self._stats("ChipHardwareTest"))

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

        hubPanels = GridLayout(cols=hubColumns)

        # Layout the grid for the hubs
        cols = 3
        if not SHOW_STATE:
            cols = cols - 1
        if SHOW_DEVICE_ID_COLUMN:
            cols = cols +1
        if SHOW_SERIAL_NUMBER_COLUMN:
            cols = cols +1
            
        widthFactor = rowSizeFactor * (3.0 / cols)
        
        mainButtonWidth = 50 * widthFactor
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
                self.mainButtons.append(widgets.button)
                if ALLOW_INDIVIDUAL_BUTTONS:
                    widgets.button.bind(on_press=self._onClickedMainButton.__get__(self, KivyView))
                    
                addTo.add_widget(widgets.button)

                widgets.deviceIdLabel = Label(id=key, text="", color=DISCONNECTED_COLOR, font_size=13 *
                                           rowSizeFactor, font_name=FONT_NAME, halign="center", size_hint_x=None, width=60 * widthFactor)
                if SHOW_DEVICE_ID_COLUMN:
                    addTo.add_widget(widgets.deviceIdLabel)
                    
                widgets.serialNumberLabel = Label(id=key, text="", color=DISCONNECTED_COLOR, font_size=8 *
                                           rowSizeFactor, font_name=FONT_NAME, halign="center", size_hint_x=None, width=60 * widthFactor)
                if SHOW_SERIAL_NUMBER_COLUMN:
                    addTo.add_widget(widgets.serialNumberLabel)

                # The state column
                widgets.stateLabel = Label(id=key, text=WAITING_TEXT, color=DISCONNECTED_COLOR, font_size=13 *
                                           rowSizeFactor, font_name=FONT_NAME, halign="center", size_hint_x=None, width=60 * widthFactor)
                if SHOW_STATE:
                    addTo.add_widget(widgets.stateLabel)

                # The label column kists of both text and a progress bar
                # positioned inside a box layout
                stateBox = BoxLayout(orientation='vertical')
                widgets.label = LabelButton(
                    id=key, text='', color=DISCONNECTED_COLOR, font_size=13 * rowSizeFactor, font_name=FONT_NAME, halign="center")
                # show output window if label clicked
                widgets.label.bind(
                    on_press=self._onShowOutput.__get__(self, KivyView))
                stateBox.add_widget(widgets.label)
                widgets.progress = ProgressBar(
                    id=key, value=0, max=1, halign="center", size_hint=(.9, 1.0 / 15))
                stateBox.add_widget(widgets.progress)
                addTo.add_widget(stateBox)

        splitter.add_widget(outputView)
        mainBox = BoxLayout(border=1)
        mainBox.add_widget(hubPanels)
        mainBox.add_widget(splitter)
        if SHOW_ALL_BUTTON:
            panelBox = FloatLayout(size_hint_y =.1, valign="center",padding=10 , background_color = BLACK_COLOR )
            all = Button(id="all", text=START_RUNNING,  pos_hint = {'x':.425, 'y':.1}, width=.2, size_hint = (0.2,.8),   halign="center", color=WHITE_COLOR)
            all.bind(on_press=self._onClickedAllButton.__get__(self, KivyView))
            panelBox.add_widget(all)
            self.add_widget(panelBox)
        self.add_widget(mainBox)

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
        Observer callback from main thread
        :param info:
        '''
        '''
    Kivy has threading issues if you try to update GUI components from a child thread.
    The solution is to add a @mainthread attribute to a function in the chlid class.
    This function will then run in the main thread. It, in turn, calls this method
    info.uid: The port
    info.state: corresponds to the states. e.g. PASSIVE_STATE
    info.stateLabel: Text label for the state, such as RUNNING_TEXT
    info.label: The label for the test case that is being run
    info.progress: number value for progress bar
    info.output: The output for the test case
    info.prompt: Any prompt to show
    '''
        uid = info['uid']
        state = info.get('state')
        stateLabel = info.get('stateLabel')
        label = info.get('label')
        progress = info.get('progress')
        output = info.get('output')
        prompt = info.get('prompt')
        deviceId = info.get('deviceId')
        serialNumber = info.get('serialNumber')

        widgets = self.widgetsMap[uid]
        if state:
            color = self._stateToColor[state]
            widgets.setColor(color)

        if stateLabel:
            widgets.stateLabel.text = stateLabel

        if label:
            widgets.label.text = label

        if progress:
            widgets.progress.value = progress

        if prompt:
            widgets.label.text = prompt

        if output:
            widgets.output = output
            # if the output detail is showing this output, it will be updated
            self._onShowOutput(None, uid)

        if deviceId:
            widgets.deviceIdLabel.text = deviceId

        if serialNumber:
            widgets.serialNumberLabel.text = serialNumber

##########################################################################
# Privates
##########################################################################

    def _onClickedAllButton(self, button):
        '''
        When the button is clicked, simulate a click on all buttons
        :param button:
        '''
        for button in self.mainButtons:
            self._onClickedMainButton(button)


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
        self.deviceIdLabel = None
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
        self.deviceIdLabel.color = color
        self.serialNumberLabel.color = color
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
    suite = None
    if len(sys.argv) == 2:
       suite = sys.argv[1]

    app = KivyApp(suite)
    try:
        app.run()
    except (KeyboardInterrupt, SystemExit):
        app.stop()

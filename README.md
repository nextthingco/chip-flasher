# CHIP-Flasher
Flashing tools for CHIP Production, as well as public usage.

## Installation
    curl "https://raw.githubusercontent.com/NextThingCo/CHIP-flasher/ww/deveop/install.sh" | sudo bash

# GUI
`main.py` launches the UI for the flasher and hwtest that is run on Kivy. It can handle any
unittest TestCase
 
It should be invoked using one of the scripts below:

'sudo ./startFlash.sh' to flash chips
'sudo ./startHardwareTest.sh' to run login/hardware test

which just pass a TestCase-derived class name to use to run the tests

# CODE
The GUI uses the Kivy Framework. It uses an MVC architecture.

* The Model is TestingThread
   * It runs unittests, failing as soon as possible
   * The unit tests are decorated to notify observers of changes
   * There are annotations (see observable_test.py) to add properties to tests
* The View is TestSuiteGUIView
   * The GUI is generated off of the udev rules file in /etc/udev/rules.d/flasher.rules
   * It sizes itself automatically to the number of hubs. It can even handle the 49 port monster
* The Controller is TestSuiteGUIApp
   * It listens to buttons clicks and launches TestingThreads
   * It updates the View from changes from the testing threads (via a queue, see below)

See the top of testSuiteGUIView.py and testSuiteGUIApp.py for constants that will change
the look and behavior of the GUI
See DeviceDescriptor.py for how the rules file is parsed

#Kivy

Kivy is a strange hybrid between animation-loop code and event driven code. For our purposes,
we want an event-driven application. Unfortunately, Kivy does not automatically handle threading
issues like other frameworks. Basically, it is not thread-safe for child threads to update the UI.
As a result, a queue is used to notify the main kivy thread that it needs to make modifications
which will be done before it updates the next frame
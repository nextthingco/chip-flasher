# CHIP-Flasher
Flashing and Testing tools for CHIP Production, as well as public usage.

## Installation
`curl https://raw.githubusercontent.com/NextThingCo/CHIP-flasher/master/install.sh | sudo bash`
This will:
* Clone the repository CHIP-flasher
* Clone the repository CHIP-tools as CHIP-flasher/flasher/tools and make it
* Clone the repository sunxi-tools as CHIP-flasher/flasher/sunxi-tools and make it
* Make a symbolic link to the FEL command in sunxi-tools
* Create desktop entry (TODO verify it works)
* Add dialout permissions

Once installed, you'll have to flash once manually to create the img files for future flashing. To do this:
`cd CHIP-flasher/flasher/tools`
`sudo ./chip-update-firmware.sh`

Now, configure udev rules as shown below

## Configuration
    The application reads the file /etc/udev/rules.d/flasher.rules
    This file maps physical ports to logical names for FEL, Fastboot, and Serial Gadget
    It is used both my linux and the application itself. The GUI and the Web applications will
    configure their output based on how you name your devices. For each port, there should be three lines, 
    one for FEL, one for Fastboot, and one for Serial gadget.
    
    The naming scheme works like this:
    chip-[id]-[column]-[fel|fastboot|serial]
    where:
    * id is a number which uniquely identifies the port in the UI
    * column is a number with which ids are grouped in the UI. This is likely a number you give to a hub
    * mode is one of fel, fastboot, or serial
For example:
'
SUBSYSTEMS=="usb",  KERNELS=="1-1.3", ATTRS{idVendor}=="1f3a", ATTRS{idProduct}=="efe8",   SYMLINK+="chip-1-1-fel"
SUBSYSTEMS=="usb",  KERNELS=="1-1.3", ATTRS{idVendor}=="1f3a", ATTRS{idProduct}=="1010",   SYMLINK+="chip-1-1-fastboot"
SUBSYSTEMS=="tty",  KERNELS=="1-1.3", ATTRS{idVendor}=="0525", ATTRS{idProduct}=="a4a7",   SYMLINK+="chip-1-1-serial"
'
For the KERNELS, see https://w.nextthing.co/doku.php?id=usb_port_mapping

## Applications
    There are currently 3 ways to run the application:
* GUI: using the Kivy framework. 
'sudo ./gui.sh'
* Web: using Flask, running on port 80
'sudo ./web.sh'
* Console: which dumps output to the terminal window
'sudo ./console.sh'

## Running
The application detects when devices are plugged in, and depending on their state (fel, or serial gadget), will either flash or run the hardware test.

# Code
The application uses a MVC architecture.
* The Model layer is the bulk of the application. The principal class is TestingThread. Each testing thread will either flash, or do a hardware test.
** Python's unittest framework is used to run the different stages of flashing/testing. Therefore, you'll see that in flasher.py that the class Flasher is a TestCase, and each stage is
a test within that class. Note the particularity that the tests are executed in alphabetical order, hence the numerical function names you'll see. 
** Custom decorators can be applied to each test (see observable_test.py). For example, you can give a test a name, an error code, and also specify the name of a 
global mutex to use when running a test to avoid issues with code that is not re-entrant. This is currently used for the SPL phase of the flashing
* The Controller is controller.py. It takes care of spawning threads and synchronizing UI updates via a queue so that all updates occur in the main thread.
* There are different views which correspond to KivyApp/View ConsoleApp/View and WebFlasher
** Polling/Updates
Polling is used to check for a change in the device state on a port (e.g. plugged in). It is also used to
trigger a check for updates in the UI queue
** KivyApp/View use Kivy's Clock class for polling and update events
** ConsoleApp/View and Webflasher use the function call_repeatedly for periodic events
** Web App
*** The web app uses Flask as a server. Communication with browsers is done using websockets.

#Logging/Stats
Currently no logging or stats takes place. Logging when running Kivy is awkward as Kivy replaces Python's logger.


The Controller (controller.py) handles the interactions between whatever view layer you choose and the TestingThreads that do the work.
The Model 

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
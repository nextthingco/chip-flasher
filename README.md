# CHIP-Flasher
Factory flasher using .chp files to flash many CHIPs in parallel

## Installation
Remember `sudo apt-get update` before you do anything.

You must
*   Run the install script which will install debian and python packages
*   Create desktop entry (TODO verify it works - should be automatic)
*   run 'python udevmaker.py', copy the file to /etc/udev/rules.d (remove any old ones), and reload the rules. Instructions for
this will appear upon exiting the tool.

## Application
*   GUI: using the Kivy framework.
`./pro.sh`

## Running
You can modify the variables in config.py to tailor the operator experience as follows:

### AUTO_START_ON_DEVICE_DETECTION = True
This setting is to provide optimal operator efficiency. As soon as a CHIP is detected, it will start flashing. When it finishes it will either be in a PASS or FAIL state. The drawback of this is that CHIPS which are DOA (201) will remain in a Waiting state indefinitely, since the flasher program never detects the device

### CLICK_TRIGGERS_ALL = True
This setting is an efficiency setting. In the case where the operator plugs in all CHIPs before flashing, he/she needs to only
click on one of the columns to start flashing all of them instead of clicking them one-by-one

### CLICK_ONLY_APPLIES_TO_SINGLE_201 = True
This setting only applies when AUTO_START_ON_DEVICE_DETECTION = False. Then if a 201 error happens, the operator must explicitly click on the device which had the error to clear out the error for the next CHIP. If this value is false, then
all 201 errors will use the CLICK_TRIGGERS_ALL setting.

##Logging/Stats
Flashing stats are logged in a sqlite database. Currently a basic UI is in the app

##fonts
On ubuntu there was an issue with the UI is showing rectangle for characters. The solution was to uninstall all droid fonts and then:
wget http://ftp.us.debian.org/debian/pool/main/f/fonts-android/fonts-droid_4.4.4r2-6_all.deb
dpkg -i fonts*.deb

### Implementation details
The application is pure Python 2.7 (not counting installed packages).

   * The entry point is in flashApp, which creates the chp_controller, the database interface, and the kivy view.
   * The chp_controller manages a group of child processes, each one endlessly flashing the CHIP plugged into its associated port.
   * Each child process, chp_flasher, reads the .chp file and writes data to it over USB
   * Synchronous communication with subprocesses uses multiprocessing.Port to send messages. This is used essentially to send
   click events to the child, or for the child to signal the parent that it is waiting for a click
   * State updates/percent complete are sent to a common multiprocessing.Queue.
   * Both the queue and the Port's connections are monitored periodically by the Kivy main loop bysetting a  Clock.schedule_interval to call the code which checks the queue and connections
   * PyDispatch is used for a publish/subscribe pattern. Currently the view and the database logger subscribe to progress(state update) events.
   
### Future directions
   * Kivy was not the best choice for the GUI, and moving to PyQt is probably a good idea, especially now that Kivy has been almost completely decoupled. This would let us easily use more advanced widgets, like QDataView.
   * Using a network-based IPC stack (instead of, or in addition to multiprocessing) would enable the GUI to run on a different machine. Either that, or a web server could be the main app.
   * A centralized database
   * Automatic integration of uploaded CHPs, along with their info stored in a database

   
   

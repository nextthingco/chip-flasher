#!/usr/bin/env python
import re
import subprocess
import curses
import time
import sys
VID_PID = "1f3a:efe8"
DEVICE_REGEX = re.compile('Bus \d+ Device (\d+)')
PORT_REGEX = re.compile('(\s*)\|__ Port (\d+): Dev (\d+).*')
BUS_REGEX = re.compile('\/:\s+Bus (\d+)')

LSUSB_CMD = ["lsusb", "-d", VID_PID]
LSUSB_T_CMD = ["lsusb", "-t"]


class UdevMaker(object):

    def __init__(self, win):
        self.lastDevice = None
        self.win = win
        self.families = [['FEL Mode', 'usb', '1f3a', 'efe8', 'fel'],
                         ['Fastboot Mode', 'usb', '1f3a', '1010', 'fastboot'],
                         ['Serial Gadget Mode', 'tty', '0525', 'a4a7', 'serial']]

    def findDevice(self):
        lsusb = subprocess.Popen(
            LSUSB_CMD,  stdout=subprocess.PIPE).communicate()[0]  # run lsusb limiting to  VID_PID above
        match = DEVICE_REGEX.search(lsusb)
        if not match: #no devices found
            return None

        device = int(match.group(1))

        # there is a delay when a CHIP is unplugged. Ignore repeat devices
        if device == self.lastDevice:
            return None
        self.lastDevice = device

        #now get the tree form of lsusb, and break it up into an array
        lsusb_t = subprocess.Popen(
            LSUSB_T_CMD, stdout=subprocess.PIPE).communicate()[0]
        lines = lsusb_t.splitlines();

        #loop through the array, producing an array of [BUS-,PORT.,PORT. ...]
        result = []
        currentDepth = 0
        for line in lines:
            busMatch = BUS_REGEX.search(line)
            if busMatch: #did we find the bus?
                bus = int(busMatch.group(1))
                name = str(bus) + "-"
                if len(result) == 0: #no bus yet, so add it
                    result.append(name)
                else:
                    result[0] = name #note that we assume only one bus
                continue

            portMatch = PORT_REGEX.search(line)
            if portMatch:
                depth = len(portMatch.group(1)) / 4 # number of spaces, grouped by 4. This is what lsusb -t does
                port = int(portMatch.group(2))
                name = str(port) + "."
                if depth > currentDepth: #if we are now under another port, add a new element to the array
                    result.append(name)
                else:
                    if depth < currentDepth: #if we've come out of a branch, prune the array
                        result = result[:depth]
                    if depth == len(result):
                        result.append(name)
                    else:
                        result[depth] = name
                currentDepth = depth
                if int(portMatch.group(3)) == device: #is this the device we're looking for?
                    break
        return (''.join(result))[:-1] #return a string from the array, removing last .

    def gatherDevices(self):
        port = 1
        hub = 1
        devices = []
        lastFound = None
        self.win.addstr("This tool lets you create a rules file to put in /etc/udev/rules.d\n")

        self.win.addstr(
            "Instructions: Press q to quit and write, h to move to the next hub\n")
        self.win.addstr("Start with hub 1\nHubs correspond to columns in the Flasher UI")
        self.win.addstr(
            "Note: Port numbers are sequential. They are unrelated to hub ports\n")
        self.win.addstr(
            "They correspond to the port numbering in the Flasher UI\n")

        self.win.addstr("Plug a jumpered CHIP into port: " + str(port) + "\n")
        while True:
            time.sleep(.1)
            ch = self.win.getch()
            if ch != -1:
                char = chr(ch)
                if char in 'qQ':
                    break
                if char in 'hH':
                    hub = hub + 1
                    self.win.addstr("Now using hub " + str(hub) + "\n")

            found = self.findDevice()
            if not found or found == lastFound: #skip when same device found again
                continue
            lastFound = found
            devices.append({'hub': hub, 'port': port, 'dev': found})
            port = port + 1
            self.win.addstr("Plug a jumpered CHIP into port: " + str(port) + "\n")

        return devices

    def produceFile(self):
        devs = self.gatherDevices()
        with open(sys.argv[1], "w") as rulesFile:
            for family in self.families: #there are currently 3 sections to the rules file: FEL, Fastboot, and Serial Gadget
                rulesFile.write("# " + family[0] + "\n")
                for dev in devs:
                    subsystem_label = "SUBSYSTEM" if family[1] == "tty" else "SUBSYSTEMS"
                    rulesFile.write(
                        '{0}=="{1}",  KERNELS=="{2}",   ATTRS{{idVendor}}=="{3}", ATTRS{{idProduct}}=="{4}",   SYMLINK+="chip-{5}-{6}-{7}"\n'.format(
                            subsystem_label, family[1], dev['dev'], family[2], family[3], dev['port'], dev['hub'], family[4]
                            )
                        )


def execute(win):
    udevMaker=UdevMaker(win)
    udevMaker.produceFile()

def main():
    if len(sys.argv) == 1:
        print "You must specify an output file. e.g. flasher.rules\n"
        return 1
    win=curses.initscr()
    curses.noecho()
    curses.cbreak()
    win.nodelay(1)
    curses.wrapper(lambda win: execute(win))
    curses.nocbreak();
    curses.echo()
    curses.endwin()
    return 0
    
    
if __name__ == "__main__":
    exit(main())




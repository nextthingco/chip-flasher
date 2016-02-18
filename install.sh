#!/bin/bash
OS=`uname`
ARM=`uname -a | grep armv7 | wc -l`
KIVY=`which kivy`

# utility variables
red=`tput setaf 1`
green=`tput setaf 2`
yellow=`tput setaf 3`
blue=`tput setaf 4`
magenta=`tput setaf 5`
cyan=`tput setaf 6`
white=`tput setaf 7`
reset=`tput sgr0`

function header { echo "${yellow}====[ ${blue}${1} ${yellow}]====${reset}"; }
function info { echo "${yellow}==> ${white}${1}${reset}"; }
function error { echo "${yellow}==> ${red}${1}${reset}"; exit 1; }

function install_linux {
    if [ "$(whoami)" != "root" ]; then
        sudo su -s "$0"
        exit
    fi
    function install_package {
        PACKAGE_MANAGER=`which apt-get`
        if [[ ! -z "${PACKAGE_MANAGER}" ]]; then
            ${PACKAGE_MANAGER} --yes --force-yes install ${@} || \
                error "could not install ${@}!"
        fi
    }
    function install_package_repo {
        if [[ ! -z "$(which add-apt-repository)" ]]; then
            sudo add-apt-repository -y ${1} && \
            sudo apt-get -y update || \
                error "could not add repo ${1}!"
        fi
    }
    header "Installing for Linux"
    export DISPLAY=:0

    sudo apt-get -y update

    if [[ -z "$( which pip )" ]]; then
        install_package python-pip \
                        python-dev
    fi
    if [[ -z "$( which gcc )" ]]; then
        install_package build-essential
    fi
    if [[ -z "$( which mkimage )" ]]; then
        install_package u-boot-tools
    fi
    if [[ -z "$(which git)" ]]; then
        install_package git
    fi
    if [[ -z "$(which gksu)" ]]; then
        install_package gksu
    fi
    if [[ -z "$(which fastboot)" ]]; then
        install_package android-tools-fastboot
    fi
    if [[ -z "$(which img2simg)" ]]; then
        install_package android-tools-fsutils
    fi
    if [[ -z "$( which pkg-config )" ]]; then
        install_package pkg-config
        install_package libusb-1.0-0-dev
    fi
    if [[ -z "$( which sqlitebrowser )" ]]; then
        install_package sqlitebrowser
    fi

#On CHIP, need to configure the package libusb
    if [[ ${ARM} ]]; then
        sudo ln -s /usr/lib/arm-linux-gnueabihf/pkgconfig/libusb-1.0.pc /usr/share/pkgconfig/libusb-1.0.pc
    fi

    PIP=`which pip`

    if [[ -z "$( which kivy )" ]]; then
        install_package python-kivy
        sudo ln -s /usr/bin/python2.7 /usr/local/bin/kivy
    fi
    if [[ -z "$( ${PIP} show pyserial)" ]]; then
        ${PIP} install pyserial || error "could not install pyserial!"
    fi
    if [[ -z "$( ${PIP} show libusb1)" ]]; then
        ${PIP} install libusb1 || error "could not install libusb1!"
    fi
    if [[ -z "$( ${PIP} show flask)" ]]; then
        ${PIP} install flask || error "could not install flask!"
    fi
    if [[ -z "$( ${PIP} show flask-socketio)" ]]; then
        ${PIP} install flask-socketio || error "could not install flask-socketio!"
    fi
    if [[ -z "$( ${PIP} show eventlet)" ]]; then
        ${PIP} install eventlet || error "could not install eventlet!"
    fi

}


function install_flasher {
    HOMEDIR="$(eval echo "~${SUDO_USER}")"
    if [[ ! -d "$HOMEDIR/Desktop/CHIP-flasher" ]]; then
        git clone --branch=master https://github.com/NextThingCo/CHIP-flasher $HOMEDIR/Desktop/CHIP-flasher
    else
        pushd $HOMEDIR/Desktop/CHIP-flasher
        git pull
        popd
    fi
    if [[ ! -d "$HOMEDIR/Desktop/CHIP-flasher/tools" ]]; then
        git clone --branch=chip/next https://github.com/NextThingCo/CHIP-tools $HOMEDIR/Desktop/CHIP-flasher/tools
    else
        pushd $HOMEDIR/Desktop/CHIP-flasher/tools
        git pull
        popd
    fi

    #Go inside flasher
    pushd CHIP-flasher/flasher

    #if no tools, clone CHIP-tools and call them just tools
    if [[ ! -d "tools" ]]; then
        info "cloning CHIP-tools"
        git clone https://github.com/NextThingCo/CHIP-tools tools
        info "making CHIP-tools"
        make -C tools
    fi

    #if no sunxi-tools, clone it
    if [[ ! -d "sunxi-tools" ]]; then
        info "cloning sunxi-tools"
        git clone https://github.com/NextThingCo/sunxi-tools
        info "making sunxi-tools"
        make -C sunxi-tools fel
        info "creating fel symbolic link"
        ln -s "$(pwd)/sunxi-tools/fel" /usr/local/bin/fel
    fi

    if [[ ! -f "$HOMEDIR/Desktop/CHIP-flasher/sunxi-tools/fel" ]]; then
        if [[ ! -d "$HOMEDIR/Desktop/CHIP-flasher/sunxi-tools" ]]; then
            git clone https://github.com/nextthingco/sunxi-tools $HOMEDIR/Desktop/CHIP-flasher/sunxi-tools
        fi
        make -C $HOMEDIR/Desktop/CHIP-flasher/sunxi-tools fel
        ln -s "$HOMEDIR/Desktop/CHIP-flasher/sunxi-tools/fel" /usr/local/bin/fel



     if [[ "$(uname)" == "Linux" ]]; then
        HOMEDIR="$(eval echo "~${SUDO_USER}")"
        SCRIPTDIR="$HOMEDIR/Desktop/CHIP-flasher" #/flasher"
        sed -i.bak "s%^\(Icon=\).*%\1${SCRIPTDIR}/logo.png%" $SCRIPTDIR/chip-flasher.desktop
        sed -i.bak "s%^\(Exec=\).*%\1${SCRIPTDIR}/gui.sh%" $SCRIPTDIR/chip-flasher.desktop
        cp ${SCRIPTDIR}/chip-flasher.desktop ${HOMEDIR}/Desktop
        chown $(logname):$(logname) ${HOMEDIR}/Desktop/chip-flasher.desktop
        chown -R $(logname):$(logname) ${SCRIPTDIR}
        usermod -a -G dialout "${SUDO_USER}"
        usermod -a -G dialout "${SUDO_USER}"

		cat <<-EOF | sudo tee /etc/udev/rules.d/flasher.rules
			# FEL Mode
			SUBSYSTEMS=="usb",      KERNELS=="1-1.3",       ATTRS{idVendor}=="1f3a",        ATTRS{idProduct}=="efe8",       SYMLINK+="chip-1-1-fel"
			SUBSYSTEMS=="usb",      KERNELS=="1-1.4",       ATTRS{idVendor}=="1f3a",        ATTRS{idProduct}=="efe8",       SYMLINK+="chip-2-1-fel"
			SUBSYSTEMS=="usb",      KERNELS=="1-1.1",       ATTRS{idVendor}=="1f3a",        ATTRS{idProduct}=="efe8",       SYMLINK+="chip-3-1-fel"
			SUBSYSTEMS=="usb",      KERNELS=="1-1.2.3",     ATTRS{idVendor}=="1f3a",        ATTRS{idProduct}=="efe8",       SYMLINK+="chip-4-1-fel"
			SUBSYSTEMS=="usb",      KERNELS=="1-1.2.4",     ATTRS{idVendor}=="1f3a",        ATTRS{idProduct}=="efe8",       SYMLINK+="chip-5-1-fel"
			SUBSYSTEMS=="usb",      KERNELS=="1-1.2.1",     ATTRS{idVendor}=="1f3a",        ATTRS{idProduct}=="efe8",       SYMLINK+="chip-6-1-fel"
			SUBSYSTEMS=="usb",      KERNELS=="1-1.2.2",     ATTRS{idVendor}=="1f3a",        ATTRS{idProduct}=="efe8",       SYMLINK+="chip-7-1-fel"
			SUBSYSTEMS=="usb",      KERNELS=="1-2.2.3",     ATTRS{idVendor}=="1f3a",        ATTRS{idProduct}=="efe8",       SYMLINK+="chip-8-2-fel"
			SUBSYSTEMS=="usb",      KERNELS=="1-2.2.1",     ATTRS{idVendor}=="1f3a",        ATTRS{idProduct}=="efe8",       SYMLINK+="chip-9-2-fel"
			SUBSYSTEMS=="usb",      KERNELS=="1-2.2.4",     ATTRS{idVendor}=="1f3a",        ATTRS{idProduct}=="efe8",       SYMLINK+="chip-10-2-fel"
			SUBSYSTEMS=="usb",      KERNELS=="1-2.4",       ATTRS{idVendor}=="1f3a",        ATTRS{idProduct}=="efe8",       SYMLINK+="chip-11-2-fel"
			SUBSYSTEMS=="usb",      KERNELS=="1-2.2.2",     ATTRS{idVendor}=="1f3a",        ATTRS{idProduct}=="efe8",       SYMLINK+="chip-12-2-fel"
			SUBSYSTEMS=="usb",      KERNELS=="1-2.1",       ATTRS{idVendor}=="1f3a",        ATTRS{idProduct}=="efe8",       SYMLINK+="chip-13-2-fel"
			SUBSYSTEMS=="usb",      KERNELS=="1-2.3",       ATTRS{idVendor}=="1f3a",        ATTRS{idProduct}=="efe8",       SYMLINK+="chip-14-2-fel"
			# Fastboot Mode
			SUBSYSTEMS=="usb",      KERNELS=="1-1.3",       ATTRS{idVendor}=="1f3a",        ATTRS{idProduct}=="1010",       SYMLINK+="chip-1-1-fastboot"
			SUBSYSTEMS=="usb",      KERNELS=="1-1.4",       ATTRS{idVendor}=="1f3a",        ATTRS{idProduct}=="1010",       SYMLINK+="chip-2-2-fastboot"
			SUBSYSTEMS=="usb",      KERNELS=="1-1.1",       ATTRS{idVendor}=="1f3a",        ATTRS{idProduct}=="1010",       SYMLINK+="chip-3-2-fastboot"
			SUBSYSTEMS=="usb",      KERNELS=="1-1.2.3",     ATTRS{idVendor}=="1f3a",        ATTRS{idProduct}=="1010",       SYMLINK+="chip-4-2-fastboot"
			SUBSYSTEMS=="usb",      KERNELS=="1-1.2.4",     ATTRS{idVendor}=="1f3a",        ATTRS{idProduct}=="1010",       SYMLINK+="chip-5-2-fastboot"
			SUBSYSTEMS=="usb",      KERNELS=="1-1.2.1",     ATTRS{idVendor}=="1f3a",        ATTRS{idProduct}=="1010",       SYMLINK+="chip-6-2-fastboot"
			SUBSYSTEMS=="usb",      KERNELS=="1-1.2.2",     ATTRS{idVendor}=="1f3a",        ATTRS{idProduct}=="1010",       SYMLINK+="chip-7-2-fastboot"
			SUBSYSTEMS=="usb",      KERNELS=="1-2.3",       ATTRS{idVendor}=="1f3a",        ATTRS{idProduct}=="1010",       SYMLINK+="chip-8-2-flashboot"
			SUBSYSTEMS=="usb",      KERNELS=="1-2.4",       ATTRS{idVendor}=="1f3a",        ATTRS{idProduct}=="1010",       SYMLINK+="chip-9-2-flashboot"
			SUBSYSTEMS=="usb",      KERNELS=="1-2.1",       ATTRS{idVendor}=="1f3a",        ATTRS{idProduct}=="1010",       SYMLINK+="chip-10-2-flashboot"
			SUBSYSTEMS=="usb",      KERNELS=="1-2.2.3",     ATTRS{idVendor}=="1f3a",        ATTRS{idProduct}=="1010",       SYMLINK+="chip-11-2-flashboot"
			SUBSYSTEMS=="usb",      KERNELS=="1-2.2.4",     ATTRS{idVendor}=="1f3a",        ATTRS{idProduct}=="1010",       SYMLINK+="chip-12-2-flashboot"
			SUBSYSTEMS=="usb",      KERNELS=="1-2.2.1",     ATTRS{idVendor}=="1f3a",        ATTRS{idProduct}=="1010",       SYMLINK+="chip-13-2-flashboot"
			SUBSYSTEMS=="usb",      KERNELS=="1-2.2.2",     ATTRS{idVendor}=="1f3a",        ATTRS{idProduct}=="1010",       SYMLINK+="chip-14-2-flashboot"
			# Serial Gadget Mode
			SUBSYSTEM=="tty",       KERNELS=="1-1.3",       ATTRS{idVendor}=="0525",        ATTRS{idProduct}=="a4a7",       SYMLINK+="chip-1-1-serial"
			SUBSYSTEM=="tty",       KERNELS=="1-1.4",       ATTRS{idVendor}=="0525",        ATTRS{idProduct}=="a4a7",       SYMLINK+="chip-2-1-serial"
			SUBSYSTEM=="tty",       KERNELS=="1-1.1",       ATTRS{idVendor}=="0525",        ATTRS{idProduct}=="a4a7",       SYMLINK+="chip-3-1-serial"
			SUBSYSTEM=="tty",       KERNELS=="1-1.2.3",     ATTRS{idVendor}=="0525",        ATTRS{idProduct}=="a4a7",       SYMLINK+="chip-4-1-serial"
			SUBSYSTEM=="tty",       KERNELS=="1-1.2.4",     ATTRS{idVendor}=="0525",        ATTRS{idProduct}=="a4a7",       SYMLINK+="chip-5-1-serial"
			SUBSYSTEM=="tty",       KERNELS=="1-1.2.1",     ATTRS{idVendor}=="0525",        ATTRS{idProduct}=="a4a7",       SYMLINK+="chip-6-1-serial"
			SUBSYSTEM=="tty",       KERNELS=="1-1.2.2",     ATTRS{idVendor}=="0525",        ATTRS{idProduct}=="a4a7",       SYMLINK+="chip-7-1-serial"
			SUBSYSTEM=="tty",       KERNELS=="1-2.3",       ATTRS{idVendor}=="0525",        ATTRS{idProduct}=="a4a7",       SYMLINK+="chip-8-2-serial"
			SUBSYSTEM=="tty",       KERNELS=="1-2.4",       ATTRS{idVendor}=="0525",        ATTRS{idProduct}=="a4a7",       SYMLINK+="chip-9-2-serial"
			SUBSYSTEM=="tty",       KERNELS=="1-2.1",       ATTRS{idVendor}=="0525",        ATTRS{idProduct}=="a4a7",       SYMLINK+="chip-10-2-serial"
			SUBSYSTEM=="tty",       KERNELS=="1-2.2.3",     ATTRS{idVendor}=="0525",        ATTRS{idProduct}=="a4a7",       SYMLINK+="chip-11-2-serial"
			SUBSYSTEM=="tty",       KERNELS=="1-2.2.4",     ATTRS{idVendor}=="0525",        ATTRS{idProduct}=="a4a7",       SYMLINK+="chip-12-2-serial"
			SUBSYSTEM=="tty",       KERNELS=="1-2.2.1",     ATTRS{idVendor}=="0525",        ATTRS{idProduct}=="a4a7",       SYMLINK+="chip-13-2-serial"
			SUBSYSTEM=="tty",       KERNELS=="1-2.2.2",     ATTRS{idVendor}=="0525",        ATTRS{idProduct}=="a4a7",       SYMLINK+="chip-14-2-serial"
		EOF
		sudo udevadm control --reload-rules
	fi
}

case "${OS}" in
	Darwin) install_darwin; install_flasher ;;
	Linux)	install_linux; install_flasher ;;
esac

# Note for socket IO, there is a little flakiness. See here
#https://github.com/miguelgrinberg/Flask-SocketIO/issues/184

#for UI - web
#sudo apt-get install libxslt-dev
#sudo apt-get install libxml2

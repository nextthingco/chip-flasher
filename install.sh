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
    if [[ -z "$(which git)" ]]; then
        install_package git
    fi
    if [[ -z "$( which sqlitebrowser )" ]]; then
        install_package sqlitebrowser
    fi
    
#remove droid fonts before installing font that works    
    sudo apt-get remove -y fonts-droid*
	wget http://ftp.us.debian.org/debian/pool/main/f/fonts-android/fonts-droid_4.4.4r2-6_all.deb
	sudo dpkg -i fonts*.deb
	rm fonts-droid_4.4.4r2-6_all.deb
#On CHIP, need to configure the package libusb
    if [[ ${ARM} ]]; then
        sudo ln -s /usr/lib/arm-linux-gnueabihf/pkgconfig/libusb-1.0.pc /usr/share/pkgconfig/libusb-1.0.pc
    fi

    PIP=`which pip`

    if [[ -z "$( which kivy )" ]]; then
        install_package python-kivy
        sudo ln -s /usr/bin/python2.7 /usr/local/bin/kivy
    fi
    if [[ -z "$( ${PIP} show libusb1)" ]]; then
        ${PIP} install libusb1 || error "could not install libusb1!"
    fi
	if [[ -z "$( ${PIP} show pyudev)" ]]; then
		${PIP} install pyudev || error "could not install pyudev!"
    fi
	if [[ -z "$( ${PIP} show pyusb)" ]]; then
		${PIP} install pyusb || error "could not install pyusb!"
    fi
	if [[ -z "$( ${PIP} show PyDispatcher)" ]]; then
		${PIP} install PyDispatcher || error "could not install PyDispatcher!"
    fi
}


function install_flasher {
	HOMEDIR="$(eval echo "~${SUDO_USER}")"
	if [[ ! -d "$HOMEDIR/Desktop/CHIP-flasher" ]]; then
		git clone --branch=pro-beta https://github.com/NextThingCo/CHIP-flasher $HOMEDIR/Desktop/CHIP-flasher
	else
		pushd $HOMEDIR/Desktop/CHIP-flasher
		git pull
		popd
	fi

	if [[ "$(uname)" == "Linux" ]]; then
		HOMEDIR="$(eval echo "~${SUDO_USER}")"
		SCRIPTDIR="$HOMEDIR/Desktop/CHIP-flasher" #/flasher"
		sed -i.bak "s%^\(Icon=\).*%\1${SCRIPTDIR}/logo.png%" $SCRIPTDIR/chip-flasher.desktop
		sed -i.bak "s%^\(Exec=\).*%\1${SCRIPTDIR}/pro.sh%" $SCRIPTDIR/chip-flasher.desktop
		cp ${SCRIPTDIR}/chip-flasher.desktop ${HOMEDIR}/Desktop
		chown $(logname):$(logname) ${HOMEDIR}/Desktop/chip-flasher.desktop
        chown -R $(logname):$(logname) ${SCRIPTDIR}
		usermod -a -G dialout "${SUDO_USER}"
		usermod -a -G dialout "${SUDO_USER}"
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

#!/bin/bash
OS=`uname`
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

function install_darwin {
	header "Installing for Darwin"
	
	if [[ -z "$( which kivy )" ]]; then
		# find brew
		BREW=`which brew`
		if [[ -z "${BREW}" ]]; then
			error "brew command not found!"
		fi
		${BREW} install libusb --HEAD || error "could not install libusb!"
		${BREW} install caskroom/cask/brew-cask || error "could not install cask!"
		${BREW} cask install kivy || error "could not install kivy!"
	fi
	KIVY=`which kivy`
	${KIVY} -m pip install libusb1 || error "could not install libusb1!"


}
function install_linux {
	function install_package {
		PACKAGE_MANAGER=`which apt-get`
		if [[ ! -z "${PACKAGE_MANAGER}" ]]; then
			${PACKAGE_MANAGER} install ${1} ||
				error "could not install ${1}!"
		fi
	}
	header "Installing for Linux"
	exit 1
	wget "http://download.teamviewer.com/download/teamviewer_i386.deb"
	dpkg -i -y "teamviewer_i386.deb"
	rm -y "teamviewer_i386.deb"
	if [[ -z "$( which kivy )" ]]; then
		install_package -y build-essential
		install_package -y python-pip
		install_package -y python-dev
		install_package -y git
		install_package -y u-boot-tools

		PIP=`which pip`
		${PIP} install cython || error "could not install cython!"
		${PIP} install kivy || error "could not install kivy!"
		${PIP} install libusb1 || error "could not install libusb1!"
	fi
}

case "${OS}" in
	Darwin) install_darwin ;;
	Linux) install_linux ;;
esac
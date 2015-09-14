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
			${PACKAGE_MANAGER} --yes --force-yes install ${@} ||
				error "could not install ${1}!"
		fi
	}
	header "Installing for Linux"

	if [[ -z "$( which teamviewer)" ]]; then
		install_package libc6:i386 \
						libgcc1:i386 \
						libasound2:i386 \
						libexpat1:i386 \
						libfontconfig1:i386 \
						libfreetype6:i386 \
						libjpeg62:i386 \
						libpng12-0:i386 \
						libsm6:i386 \
						libxdamage1:i386 \
						libxext6:i386 \
						libxfixes3:i386 \
						libxinerama1:i386 \
						libxrandr2:i386 \
						libxrender1:i386 \
						libxtst6:i386 \
						zlib1g:i386
		wget "http://download.teamviewer.com/download/teamviewer_i386.deb"
		dpkg -i "teamviewer_i386.deb"
		rm -y "teamviewer_i386.deb"
	fi
	if [[ -z "$( which pip )" ]]; then
		install_package python-pip \
						python-dev
	fi
	if [[ -z "$( which gcc )" ]]; then
		install_package build-essential \
						git
	fi
	if [[ -z "$( which mkimage )" ]]; then
		install_package u-boot-tools
	fi
	if [[ -z "$( which kivy )" ]]; then
		install_package mesa-common-dev \
						libgl1-mesa-dev \
						python-setuptools \
						python-pygame \
						python-opengl \
						python-gst0.10 \
						python-enchant \
						gstreamer0.10-plugins-good \
						libgles2-mesa-dev
		PIP=`which pip`
		${PIP} install --upgrade Cython==0.21 || error "could not install cython!"
		${PIP} install kivy || error "could not install kivy!"
		${PIP} install libusb1 || error "could not install libusb1!"
		sudo ln -s /usr/bin/python2.7 /usr/bin/kivy
	fi
}
function install_flasher {
	install_package git
	install_package gksu
	if [[ ! -d "flasher" ]];then
		git clone https://github.com/NextThingCo/CHIP-flasher.git flasher
	fi
	if [[ ! -d "flasher/tools" ]];then
		git clone https://github.com/NextThingCo/CHIP-tools flasher/tools
	fi
	if [[ ! -f "flasher/sunxi-tools/fel" ]];then
		install_package libusb-1.0-0-dev android-tools-fastboot
		if [[ ! -d "flasher/sunxi-tools" ]];then
			git clone https://github.com/linux-sunxi/sunxi-tools flasher/sunxi-tools
		fi
		make -C flasher/sunxi-tools fel
		ln -s "$(pwd)/flasher/sunxi-tools/fel" /usr/bin/fel
	fi
	chmod -R 777 flasher

  	cp flasher/chip-flasher.desktop Desktop
	chown $(logname):$(logname) Desktop/chip-flasher.desktop
#	DISPLAY=:0 kivy flasher/main.py
}
function install_tmate {
	if [[ -z "$(which tmate)" ]]; then
		sudo apt-get -y install software-properties-common && \
		sudo add-apt-repository -y ppa:nviennot/tmate      && \
		sudo apt-get -y update                             && \
		sudo apt-get -y install tmate
	fi
}

case "${OS}" in
	Darwin) install_darwin; install_flasher ;;
	Linux) install_linux; install_flasher; install_tmate ;;
esac

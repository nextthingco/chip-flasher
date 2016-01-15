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

	# install kivy
	if [[ -z "$( which kivy )" ]]; then
		# find brew
		BREW=`which brew`
		if [[ -z "${BREW}" ]]; then
			error "brew command not found!"
		fi
		${BREW} install caskroom/cask/brew-cask || error "could not install cask!"
		${BREW} cask install kivy || error "could not install kivy!"
	fi

	# install libusb into kivy
	KIVY=`which kivy`
	SCRIPT_PATH="${KIVY}";
	if([ -h "${SCRIPT_PATH}" ]) then
	  while([ -h "${SCRIPT_PATH}" ]) do SCRIPT_PATH=`readlink "${SCRIPT_PATH}"`; done
	fi
	SCRIPT_PATH=$(python -c "import os; print os.path.realpath(os.path.dirname('${SCRIPT_PATH}'))")
	
	if [[ ! -f "${SCRIPT_PATH}/lib/libusb-1.0.dylib" ]]; then
		TMP_PATH=`mktemp -d -t chipflasher.XXXXXX`

		pushd $TMP_PATH
			git clone https://github.com/libusb/libusb.git
			pushd libusb
				./autogen.sh
				./configure --disable-dependency-tracking --prefix="${SCRIPT_PATH}"
				make -j4
				make install
			popd
		popd
	fi
	${KIVY} -m pip install libusb1 || error "could not install libusb1!"


}
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
	if [[ -z "img2simg" ]]; then
		install_package android-tools-fsutils
	fi
	
	PIP=`which pip`

	if [[ -z "$( which kivy )" ]]; then
		install_package mesa-common-dev \
						libgl1-mesa-dev \
						python-setuptools \
						python-pygame \
						python-opengl \
						python-gst0.10 \
						python-enchant \
						gstreamer0.10-plugins-good \
						libgles2-mesa-dev \
						libusb-1.0-0-dev
		${PIP} install --upgrade Cython==0.21 || error "could not install cython!"
		${PIP} install kivy || error "could not install kivy!"
		sudo ln -s /usr/bin/python2.7 /usr/local/bin/kivy
	fi
	if [[ -z "$( ${PIP} show libusb1)" ]]; then
		${PIP} install libusb1 || error "could not install libusb1!"
	fi
    if [[ -z "$( ${PIP} show pexpect)" ]]; then
        ${PIP} install pexpect || error "could not install pexpect!"
    fi
	if [[ -z "$( ${PIP} show pyserial)" ]]; then
		${PIP} install pyserial || error "could not install pyserial!"
	fi
	# if [[ -z "$(which tmate)" ]]; then
	# 	install_package software-properties-common && \
	# 	install_package_repo ppa:nviennot/tmate && \
	# 	install_package tmate || \
	# 		error "Could not install tmate!"
	# fi
}
function install_flasher {
	HOMEDIR="$(eval echo "~${SUDO_USER}")"
	if [[ ! -d "$HOMEDIR/Desktop/CHIP-flasher" ]]; then
		git clone --branch=edadoc https://github.com/NextThingCo/CHIP-flasher $HOMEDIR/Desktop/CHIP-flasher
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

	# if [[ ! -d "Desktop/CHIP-flasher/testjig" ]]; then
	# 	git clone https://github.com/NextThingCo/ChipTestJig Desktop/CHIP-flasher/testjig
	# else
	# 	pushd Desktop/CHIP-flasher/testjig
	# 	git pull
	# 	popd
	# fi
	if [[ ! -f "$HOMEDIR/Desktop/CHIP-flasher/sunxi-tools/fel" ]]; then
		if [[ ! -d "$HOMEDIR/Desktop/CHIP-flasher/sunxi-tools" ]]; then
			git clone https://github.com/nextthingco/sunxi-tools $HOMEDIR/Desktop/CHIP-flasher/sunxi-tools
		fi
		if [[ "${OS}" == "Darwin" ]]; then
			if [[ -z "$(which fel)" ]]; then
				pushd $HOMEDIR/Desktop/CHIP-flasher/sunxi-tools
					cat <<-EOF > fix-osx.patch
						diff --git a/include/endian_compat.h b/include/endian_compat.h
						index e463a52..a927bbd 100644
						--- a/include/endian_compat.h
						+++ b/include/endian_compat.h
						@@ -29,6 +29,9 @@
						 #define le32toh(x) CFSwapInt32LittleToHost(x)
						 #define htole16(x) CFSwapInt16HostToLittle(x)
						 #define le16toh(x) CFSwapInt16LittleToHost(x)
						+
						+
						+#define be32toh(x) CFSwapInt32BigToHost(x)
						 #else
						 #include <endian.h>
						 #endif

						diff --git a/fel.c b/fel.c
						old mode 100644
						new mode 100755
						index 98e8d89..5f55d34
						--- a/fel.c
						+++ b/fel.c
						@@ -1081,6 +1081,8 @@ int main(int argc, char **argv)
						 		aw_fel_execute(handle, uboot_entry);
						 	}
						 
						+	libusb_release_interface(handle, 0);
						+
						 #if defined(__linux__)
						 	if (iface_detached >= 0)
						 		libusb_attach_kernel_driver(handle, iface_detached);
					EOF
				patch -p1 < fix-osx.patch
				popd
			fi
		fi
		make -C $HOMEDIR/Desktop/CHIP-flasher/sunxi-tools fel
		ln -s "$HOMEDIR/Desktop/CHIP-flasher/sunxi-tools/fel" /usr/local/bin/fel
	fi

	if [[ "$(uname)" == "Linux" ]]; then
		HOMEDIR="$(eval echo "~${SUDO_USER}")"
		SCRIPTDIR="$HOMEDIR/Desktop/CHIP-flasher" #/flasher"
		sed -i.bak "s%^\(Icon=\).*%\1${SCRIPTDIR}/logo.png%" $SCRIPTDIR/chip-flasher.desktop
		sed -i.bak "s%^\(Exec=\).*%\1${SCRIPTDIR}/startFlash.sh%" $SCRIPTDIR/chip-flasher.desktop
		cp ${SCRIPTDIR}/chip-flasher.desktop ${HOMEDIR}/Desktop
		chown $(logname):$(logname) ${HOMEDIR}/Desktop/chip-flasher.desktop
        chown -R $(logname):$(logname) ${SCRIPTDIR}
		usermod -a -G dialout "${SUDO_USER}"
		usermod -a -G dialout "${SUDO_USER}"

		cat <<-EOF | sudo tee /etc/udev/rules.d/99-allwinner.rules
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

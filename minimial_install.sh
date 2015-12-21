apt-get install python-kivy python-serial
ln -s /usr/bin/python2.7 /usr/local/bin/kivy
ln -s ~/Desktop/CHIP-tools ~/Desktop/CHIP-flasher/flasher/tools

#for web
apt-get install python-dev
pip install flask
pip install flask-socketio
pip install eventlet
#https://github.com/miguelgrinberg/Flask-SocketIO/issues/184
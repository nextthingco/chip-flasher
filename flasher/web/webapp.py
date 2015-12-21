from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
from flasher import Controller
from flasher import call_repeatedly
from flasher import RunState
import requests
import json
from logging import log
import logging
import sys

import threading
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
# app.debug=True
socketio = SocketIO(app)
stateToClass = {RunState.PASSIVE_STATE: 'passive', RunState.PASS_STATE: 'success', RunState.FAIL_STATE: 'fail', RunState.PROMPT_STATE: 'prompt', RunState.ACTIVE_STATE:'active', RunState.PAUSED_STATE:'paused', RunState.IDLE_STATE: 'passive', RunState.DISCONNECTED_STATE: 'disconnected'}


class WebFlasher():
    def __init__(self):
        self.controller = None
        logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
        self.log = logging.getLogger("flash")
        self.base_url = None
        
        
#     def run(self):
    def start(self):
        self.controller = Controller(self.log)
        controller = self.controller
        controller.setTimeoutMultiplier(2.3)
        controller.configure()
        socketio.emit("stateChange","start",broadcast=True)

        controller.addStateListener(lambda info: self.stateListener(info))
         
        call_repeatedly(1, lambda: controller.onPollingTick(0))
        call_repeatedly(.1,lambda: controller.onUpdateTrigger(0))
 
    def stateListener(self,info):
        if not self.base_url: #ignore until we have a page listening
            return
        url = self.base_url + '/stateChange'
        fullInfo = self.controller.stateInfo[info['uid']].copy() # get complete info, not just what changed
        if fullInfo.get('state'):
            fullInfo['stateClass'] = stateToClass[fullInfo['state']]
        if fullInfo.get('label'):
            fullInfo['label'] = fullInfo['label'].replace("\n",'<br>')
        if fullInfo.get('stateLabel'):
            fullInfo['stateLabel'] = fullInfo['stateLabel'].replace("\n",'<br>')

        payload = fullInfo #{'info': info}
        headers = {'content-type': 'application/json'}

        requests.post(url, data=json.dumps(payload), headers=headers) #post message to flask. This makes sure that socketio uses main thread





@app.route('/stateChange',methods=['POST'])
def stateChange():
    info = request.get_json()
    socketio.emit("stateChange",info,broadcast = True)
    return jsonify("")

@app.route('/js/<path:path>')
def send_js(path):
    return send_from_directory('js', path)
        
@app.route('/css/<path:path>')
def send_css(path):
    return send_from_directory('css', path)

stateToClass = {RunState.PASSIVE_STATE: 'passive', RunState.PASS_STATE: 'success', RunState.FAIL_STATE: 'fail', RunState.PROMPT_STATE: 'prompt', RunState.ACTIVE_STATE:'active', RunState.PAUSED_STATE:'paused', RunState.IDLE_STATE: 'passive', RunState.DISCONNECTED_STATE: 'disconnected'}
    
    
@app.route('/')
def mainPage():
    webFlasher.base_url = request.base_url
    return render_template('deviceTable.html', stateInfoArray=webFlasher.controller.stateInfo.values(), stateToClass=stateToClass)
 



if __name__ == '__main__':
    webFlasher = WebFlasher()
    webFlasher.start()
    socketio.run(app)
    

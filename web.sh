#!/bin/bash

DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
DISPLAY=:0 sudo python -m ${DIR}/web/webapp

#python -m web/webapp
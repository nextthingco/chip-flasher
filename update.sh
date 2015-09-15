#!/bin/bash

SCRIPTDIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )

pushd $SCRIPTDIR
git reset --hard HEAD
git pull

pushd tools
git reset --hard HEAD
popd

popd

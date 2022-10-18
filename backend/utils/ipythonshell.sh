#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
export GOOGLE_APPLICATION_CREDENTIALS=../common/keys/videosdb-testing.json
export IPYTHONDIR=$SCRIPT_DIR/ipython_config
oldpwd=$(pwd)
cd $SCRIPT_DIR/..
#$SCRIPT_DIR/load-dotenv $SCRIPT_DIR/../common/env/testing.txt poetry run ipython3 --no-confirm-exit --no-banner --InteractiveShellApp.extensions=autoreload
poetry run ipython3 --no-confirm-exit --no-banner --InteractiveShellApp.extensions=autoreload
cd $oldpwd



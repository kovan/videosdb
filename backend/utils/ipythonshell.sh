#!/bin/sh
export GOOGLE_APPLICATION_CREDENTIALS=../common/keys/videosdb-testing.json
IPYTHONDIR=utils/ipython_config utils/load-dotenv ../common/env/testing.txt poetry run ipython3 --no-confirm-exit --no-banner --InteractiveShellApp.extensions=autoreload


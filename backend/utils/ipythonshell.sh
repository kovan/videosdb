#!/bin/sh
IPYTHONDIR=./ipython_config ./load-dotenv ../common/env/testing.txt  ipython3 --no-confirm-exit --no-banner --InteractiveShellApp.extensions=autoreload


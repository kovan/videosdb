#!/bin/sh
IPYTHONDIR=utils/ipython_config utils/load-dotenv ../common/env/testing.txt poetry run ipython3 --no-confirm-exit --no-banner --InteractiveShellApp.extensions=autoreload


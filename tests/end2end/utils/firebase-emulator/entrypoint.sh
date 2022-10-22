#!/bin/bash
export JAVA_TOOL_OPTIONS="-Xmx3g"
firebase use default;
firebase emulators:start --debug

#!/bin/bash
firebase use $GCP_PROJECT
firebase emulators:start $@

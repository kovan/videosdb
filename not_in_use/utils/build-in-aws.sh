#/bin/bash

aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin 570555265801.dkr.ecr.ap-south-1.amazonaws.com
export REPO=570555265801.dkr.ecr.ap-south-1.amazonaws.com/

utils/build.sh $@
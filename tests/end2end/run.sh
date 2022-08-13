#!bin/bash
function cleanup() {
    kill $EMU_PID
}

#sudo apt install openjdk-18-jre -y
#sudo npm install -g firebase-tools
#service docker start
firebase emulators:start --export-on-exit emulator-data &
EMU_PID=$!
trap 'cleanup' 2 # capture SIGINT

docker build ../../backend
docker run --rm -e LOGLEVEL=DEBUG backend poetry run python -m videosdb -c


cleanup()
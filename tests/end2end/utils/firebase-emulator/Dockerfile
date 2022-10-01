FROM ubuntu:22.04
#RUN wget https://nodejs.org/dist/v16.16.0/node-v16.16.0-linux-x64.tar.xz
RUN apt update
RUN apt install curl -y
RUN curl -fsSL https://deb.nodesource.com/setup_16.x | bash -

RUN apt-get install -y nodejs
RUN apt-get install -y openjdk-18-jre-headless
RUN npm install -g firebase-tools
RUN firebase setup:emulators:firestore
RUN firebase setup:emulators:ui

WORKDIR /root

COPY . .


ENTRYPOINT [ "/root/entrypoint.sh" ]

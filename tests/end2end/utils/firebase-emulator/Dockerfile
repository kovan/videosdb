FROM debian:bullseye-slim
RUN echo 'root:toor' | chpasswd
ENV DEBIAN_FRONTEND="noninteractive"
RUN apt update
RUN apt install curl -y
RUN curl -fsSL https://deb.nodesource.com/setup_16.x | bash -
RUN apt-get install -y nodejs

RUN apt-get install -y default-jre-headless
RUN apt clean

RUN npm install -g firebase-tools
RUN firebase setup:emulators:firestore
RUN firebase setup:emulators:ui

WORKDIR /root

COPY . .


ENTRYPOINT [ "/root/entrypoint.sh" ]

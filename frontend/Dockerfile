FROM debian:bullseye-slim
RUN echo 'root:toor' | chpasswd
ENV DEBIAN_FRONTEND="noninteractive"
RUN apt update
RUN apt install curl -y
RUN curl -fsSL https://deb.nodesource.com/setup_16.x | bash -
RUN apt-get install -y nodejs
RUN apt clean

RUN npm i -g yarn
ENV YARN_CACHE_FOLDER /yarn
VOLUME /yarn
WORKDIR /app/


COPY package.json .
COPY yarn.lock .


RUN yarn install

COPY . .

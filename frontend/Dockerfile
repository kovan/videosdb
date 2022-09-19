FROM node:18

ENV YARN_CACHE_FOLDER /yarn
VOLUME /yarn
WORKDIR /app/


COPY package.json .
COPY yarn.lock .


RUN yarn install

COPY . .

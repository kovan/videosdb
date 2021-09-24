FROM node:latest

WORKDIR /src

COPY package.json .
COPY yarn.lock .

RUN yarn install

COPY . .

RUN yarn generate


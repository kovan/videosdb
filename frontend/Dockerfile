FROM node:14

WORKDIR /src

COPY package.json .
COPY yarn.lock .

RUN yarn install

COPY . .



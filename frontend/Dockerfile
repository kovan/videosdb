FROM node:latest

WORKDIR /src

COPY package.json .
COPY yarn.lock .

RUN yarn install

COPY . .

CMD yarn generate


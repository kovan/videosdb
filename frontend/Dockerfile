FROM node:latest

WORKDIR /src

COPY package.json .
COPY yarn.lock .

RUN yarn install

COPY . .

RUN yarn build

ENV NODE_ENV=production
ENV HOST 0.0.0.0

EXPOSE 3000


CMD [ "yarn", "start" ]

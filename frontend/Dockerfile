FROM node:12


# global install & update
RUN npm i -g npm && npm i -g yarn --force

# Create app directory
WORKDIR /app
ADD package.json yarn.lock /app/
RUN yarn
ADD . /app/
RUN yarn build


ENV HOST 0.0.0.0
EXPOSE 3000

# start command
CMD [ "yarn", "start" ]
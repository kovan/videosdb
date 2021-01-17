FROM node:12


# global install & update
RUN npm i -g npm && npm i -g yarn --force

# Create app directory
WORKDIR /app
ADD . /app/

#RUN rm yarn.lock
RUN yarn
RUN yarn build

ENV HOST 0.0.0.0
EXPOSE 3000

# start command
CMD [ "yarn", "start" ]
FROM node:18

ENV YARN_CACHE_FOLDER /yarn
WORKDIR /app/

# Add entrypoint script to handle yarn cache
RUN mkdir -p $YARN_CACHE_FOLDER

COPY package.json .
COPY yarn.lock .


RUN sh -c "yarn config set cache-folder $YARN_CACHE_FOLDER && yarn install"

COPY . .


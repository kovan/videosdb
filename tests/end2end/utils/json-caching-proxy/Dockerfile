FROM node:16
RUN npm install -g json-caching-proxy
COPY ytapi_responses.har .
ENTRYPOINT [ "json-caching-proxy", "-p", "8080", "-l", "-H", "ytapi_responses.har", "-u", "https://www.googleapis.com/youtube/v3" ]
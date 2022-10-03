FROM node:16
WORKDIR "/app"
RUN git clone https://github.com/kovan/json-caching-proxy
WORKDIR "/app/json-caching-proxy"
RUN npm install
COPY ytapi_responses.har .
COPY json-caching-proxy.playback.config.json config.json
ENTRYPOINT [ "node", "bin.js", "--config", "config.json"]

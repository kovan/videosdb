FROM node:16
RUN npm install -g json-caching-proxy
COPY ytapi_responses.har .
COPY json-caching-proxy.json.config .
ENTRYPOINT [ "json-caching-proxy", "--config", "json-caching-proxy.json.config"]
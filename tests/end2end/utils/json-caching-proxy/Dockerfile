FROM debian:bullseye-slim
RUN echo 'root:toor' | chpasswd
ENV DEBIAN_FRONTEND="noninteractive"
RUN apt update
RUN apt install curl -y
RUN curl -fsSL https://deb.nodesource.com/setup_16.x | bash -
RUN apt-get install -y nodejs
RUN apt-get install -y git --no-install-suggests --no-install-recommends
RUN apt clean

WORKDIR "/app"
RUN git clone https://github.com/kovan/json-caching-proxy
WORKDIR "/app/json-caching-proxy"
RUN npm install
COPY ytapi_responses.har .
COPY json-caching-proxy.playback.config.json config.json
ENTRYPOINT [ "node", "bin.js", "--config", "config.json"]

# Multi-stage Docker build for VideosDB Fulcro
# Stage 1: Build Clojure + ClojureScript
FROM clojure:temurin-21-tools-deps-bookworm-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs npm git curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Clojure deps
COPY deps.edn ./
RUN clojure -P

# Install npm deps
COPY package.json ./
RUN npm install

# Copy shadow-cljs config
COPY shadow-cljs.edn ./

# Copy source code
COPY src/ src/
COPY resources/ resources/
COPY bb.edn ./

# Build ClojureScript (client + SSR)
RUN npx shadow-cljs release client ssr

# AOT compile Clojure
RUN clojure -M -e "(compile 'videosdb.cli)"

# Stage 2: Runtime image
FROM eclipse-temurin:21-jre-jammy AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy compiled artifacts
COPY --from=builder /app/deps.edn ./
COPY --from=builder /app/.cpcache ./.cpcache
COPY --from=builder /app/src/main src/main
COPY --from=builder /app/src/shared src/shared
COPY --from=builder /app/resources resources
COPY --from=builder /app/target/ssr.js target/ssr.js
COPY --from=builder /app/node_modules node_modules
COPY --from=builder /app/bb.edn ./

# Copy common directory (service account keys, firebase configs)
COPY ../../common common

ENTRYPOINT ["clojure"]
CMD ["-M:cli", "-c"]

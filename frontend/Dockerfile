FROM node:latest as builder

WORKDIR /src

COPY package.json .

RUN yarn install \
  --network-timeout 100000 \
  --prefer-offline \
  --frozen-lockfile \
  --non-interactive \
  --production=false

COPY . .

RUN yarn build

RUN rm -rf node_modules && \
  NODE_ENV=production yarn install \
  --network-timeout 100000 \
  --prefer-offline \
  --pure-lockfile \
  --non-interactive \
  --production=true

FROM node:alpine

WORKDIR /src

COPY --from=builder /src  .


ENV HOST 0.0.0.0
ENV NODE_ENV=production
EXPOSE 3000


CMD [ "npx", "nuxt", "start" ]

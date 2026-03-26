FROM node:lts-alpine

ENV COREPACK_HOME=/usr/local/share/corepack
RUN corepack enable
RUN corepack prepare pnpm@9.15.9 --activate

WORKDIR /app
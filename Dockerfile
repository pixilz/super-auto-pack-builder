FROM node:lts-alpine

RUN corepack enable
RUN corepack prepare pnpm@9.15.9 --activate

WORKDIR /app
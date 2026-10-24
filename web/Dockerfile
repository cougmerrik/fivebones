FROM node:24.14.0-alpine AS build
WORKDIR /app
RUN corepack enable
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY web/package.json web/package.json
COPY extension/package.json extension/package.json
COPY packages/ui/package.json packages/ui/package.json
COPY packages/contracts/package.json packages/contracts/package.json
RUN pnpm install --frozen-lockfile
COPY web ./web
COPY packages ./packages
COPY *_bg.png ./
COPY title.png ./
COPY pip*.png ./
ARG VITE_API_BASE_URL=http://localhost:8000
ARG VITE_WS_BASE_URL=
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL VITE_WS_BASE_URL=$VITE_WS_BASE_URL
RUN pnpm build:web
FROM nginx:1.27.4-alpine
ENV PORT=8080
COPY web/nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/web/dist /usr/share/nginx/html
EXPOSE 8080

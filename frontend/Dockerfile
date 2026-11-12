# Frontend sala_web: build de produção servido pelo nginx (ticket 42, ADR-0001).
# O dev server do Vite (npm run dev) fica só para desenvolvimento local, fora da imagem.
#
# As variáveis VITE_* são lidas no BUILD (o Vite as grava no JavaScript gerado), por isso entram como
# build args. Mudou VITE_API_URL? Refaça a imagem: docker compose up --build.

# ---------- 1) build ----------
FROM node:22-alpine AS build
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY . .

ARG VITE_API_URL=http://localhost:8000
ARG VITE_UPLOAD_MAX_MB=5
ENV VITE_API_URL=${VITE_API_URL} \
    VITE_UPLOAD_MAX_MB=${VITE_UPLOAD_MAX_MB}
RUN npm run build

# ---------- 2) servidor estático ----------
FROM nginx:1.28-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80

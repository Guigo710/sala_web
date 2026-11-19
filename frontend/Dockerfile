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
# A CSP (ticket 52) precisa da origem da API: ela sai do MESMO build arg que o Vite usou.
# Só aceita http(s)://host[:porta][/caminho]; qualquer outra coisa (aspas, espaço, ;) derruba o build
# em vez de virar cabeçalho quebrado. O caminho é descartado: a CSP usa a origem, que cobre /uploads.
ARG VITE_API_URL=http://localhost:8000
COPY nginx.conf /tmp/nginx.conf.template
RUN API_ORIGIN="$(printf '%s' "$VITE_API_URL" | sed -nE 's#^(https?://[A-Za-z0-9.-]+(:[0-9]+)?)(/[A-Za-z0-9._~/-]*)?$#\1#p')" \
    && [ -n "$API_ORIGIN" ] || { echo "VITE_API_URL inválida para a CSP: '$VITE_API_URL'" >&2; exit 1; } \
    && export API_ORIGIN \
    && envsubst '${API_ORIGIN}' < /tmp/nginx.conf.template > /etc/nginx/conf.d/default.conf \
    && rm /tmp/nginx.conf.template \
    && grep -q "connect-src 'self' $API_ORIGIN;" /etc/nginx/conf.d/default.conf \
    && nginx -t
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80

# Frontend sala_web: dev server do Vite (ver docker-compose.yml, serviço "frontend").
# VITE_API_URL vem do ambiente do Compose e é lido pelo Vite ao subir.
FROM node:22-slim

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]

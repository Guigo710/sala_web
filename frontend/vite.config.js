import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Dev server (npm run dev) só para desenvolvimento: escuta apenas em localhost (ticket 42: ele expõe o
// código-fonte e não deve ficar acessível pela rede; use `npm run dev -- --host` se precisar de outro aparelho).
// A imagem Docker serve o build com nginx (Dockerfile, nginx.conf). O preview serve dist/ (CI e E2E).
export default defineConfig({
  plugins: [react()],
  server: {
    host: 'localhost',
    port: 5173,
    strictPort: true,
  },
  preview: {
    host: '0.0.0.0',
    port: 5173,
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/testes/setup.js'],
    // e2e/ é do Playwright (npx playwright test), não do Vitest.
    include: ['src/**/*.test.{js,jsx}'],
    css: false,
  },
});

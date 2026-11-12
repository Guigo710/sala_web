import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// O dev server escuta em 0.0.0.0:5173 (ver Dockerfile e docker-compose.yml).
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
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

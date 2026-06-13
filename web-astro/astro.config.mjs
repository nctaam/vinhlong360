// @ts-check
import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://vinhlong360.vn',
  output: 'static',
  server: { port: 4360 },
  vite: {
    server: {
      proxy: {
        '/api': 'http://localhost:8360',
        '/auth': 'http://localhost:8360',
        '/admin': 'http://localhost:8360',
      }
    }
  }
});

import path from 'node:path'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: true,
    port: 5174,
    allowedHosts: true,
    proxy: {
      // Real Lore backend (server.py), run locally with `python server.py` from redtail-site.
      '/api': 'http://localhost:8100',
    },
  },
  plugins: [
    react(),
  ]
});

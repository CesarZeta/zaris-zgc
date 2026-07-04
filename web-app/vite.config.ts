import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // dev: el backend FastAPI local (evita configurar CORS/URLs en el cliente)
      '/api': 'http://localhost:8021',
    },
  },
})

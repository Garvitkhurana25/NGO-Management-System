import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In dev, Vite proxies every /api request to the Django dev server on :8000,
// so the browser talks to one origin and CORS is never involved.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
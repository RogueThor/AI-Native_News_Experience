import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Auth
      '/login': 'http://127.0.0.1:8000',
      '/logout': 'http://127.0.0.1:8000',
      '/user': 'http://127.0.0.1:8000',
      // News / feed APIs
      '/news': 'http://127.0.0.1:8000',
      '/interaction': 'http://127.0.0.1:8000',
      // Article lenses
      '/article': 'http://127.0.0.1:8000',
      // Arc JSON API only — NOT /arc/* (that is the React SPA route)
      '/arc/data': 'http://127.0.0.1:8000',
      // Static assets (AI anchor GIF etc.)
      '/static': 'http://127.0.0.1:8000',
      // Chat REST fallback
      '/api/chat': 'http://127.0.0.1:8000',
      // WebSocket (chat + feed)
      '/ws': {
        target: 'ws://127.0.0.1:8000',
        ws: true,
        changeOrigin: true,
      },
    },
  },
})

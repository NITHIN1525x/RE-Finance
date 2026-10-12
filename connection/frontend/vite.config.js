import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The dev server proxies /api to Django, so the browser only ever talks to one origin (no CORS).
// changeOrigin stays false so Django sees Host: localhost:5173, which matches the Origin header
// for its CSRF check. The OAuth callback goes straight to Django on :8000 (registered redirect URI).
export default defineConfig({
  plugins: [react()],
  server: {
    host: 'localhost',
    port: 5173,
    strictPort: true, // FRONTEND_URL in backend.env assumes exactly this port
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: false },
    },
  },
  build: {
    sourcemap: false,
  },
})

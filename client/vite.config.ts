import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    allowedHosts: true,
    proxy: {
      '/.proxy/api': {
        target: 'http://localhost:5001',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/.proxy/, ''),
      },
      '/socket.io': {
        target: 'ws://localhost:5001',
        changeOrigin: true,
        ws: true,
      },
    }

  },
})

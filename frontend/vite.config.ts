import http from 'node:http'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

/** Avoid keep-alive sockets to uvicorn — stale ones cause ECONNRESET hangs in the browser. */
const apiAgent = new http.Agent({ keepAlive: false, maxSockets: 20 })

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        timeout: 30_000,
        proxyTimeout: 30_000,
        agent: apiAgent,
        configure: (proxy) => {
          proxy.on('error', (err, _req, res) => {
            console.error('[vite api proxy]', err.message)
            const r = res as http.ServerResponse | undefined
            if (r && !r.headersSent) {
              r.writeHead(502, { 'Content-Type': 'application/json' })
              r.end(JSON.stringify({ detail: `API proxy error: ${err.message}` }))
            }
          })
        },
      },
    },
  },
})

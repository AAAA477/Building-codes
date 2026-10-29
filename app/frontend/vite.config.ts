import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
// Optional: VITE_PROXY=http://127.0.0.1:8012 with VITE_API_BASE=/api avoids CORS when testing against another backend port.
const proxy = process.env.VITE_PROXY
export default defineConfig({ plugins: [react()], server: { port: 5173, ...(proxy ? { proxy: { '/api': proxy } } : {}) } })

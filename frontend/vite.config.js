import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,     // 0.0.0.0 for containers/Codespaces
    port: 5173,
    strictPort: true
  }
})

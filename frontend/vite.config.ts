import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// base: '/static/' so that built assets resolve through FastAPI's existing
// StaticFiles mount at /static — no backend change needed.
// Build output goes to ../static (the directory FastAPI already serves).
export default defineConfig({
  base: '/static/',
  plugins: [react()],
  server: {
    proxy: {
      '/ask': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: '../static',
    emptyOutDir: false,
    assetsDir: 'assets',
    chunkSizeWarningLimit: 800,
    rollupOptions: {
      output: {
        manualChunks: {
          three: ['three'],
          react: ['react', 'react-dom'],
          motion: ['framer-motion'],
        },
      },
    },
  },
});

import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  // Relative base so the app works under a GitHub project-Pages subpath
  // (e.g. /SectorPulse/) as well as at a domain root (Vercel/Netlify).
  base: './',
  plugins: [react()],
  build: {
    target: 'es2020',
  },
});

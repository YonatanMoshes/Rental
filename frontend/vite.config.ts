/**
 * Vite configuration for React frontend
 * 
 * Development:
 *   - Hot module replacement (HMR)
 *   - Proxy API calls to backend (configurable via VITE_API_PROXY_TARGET)
 *   - Default backend: http://127.0.0.1:8000
 * 
 * Production:
 *   - Optimized build
 *   - Code splitting
 *   - Source maps (optional)
 */

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Allow overriding backend URL via environment variable
const apiProxyTarget = process.env.VITE_API_PROXY_TARGET ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    // Proxy configuration: redirect API calls to backend
    // Prevents CORS issues during development
    proxy: {
      "/api": apiProxyTarget,      // Fleet API endpoints
      "/health": apiProxyTarget,   // Health check
      "/metrics": apiProxyTarget   // Prometheus metrics
    }
  }
});

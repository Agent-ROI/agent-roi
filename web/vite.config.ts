import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// During `vite dev`, proxy API calls to the FastAPI backend so the frontend and
// backend can run on separate ports without CORS hassle.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
  build: {
    outDir: "dist",
  },
});

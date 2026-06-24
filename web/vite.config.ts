import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Proxy all backend routes to the Python server (serve.py on :8008)
const backend = "http://127.0.0.1:8008";
const routes = ["/api", "/build", "/styles", "/shows", "/show", "/save", "/render", "/refs", "/output", "/characters", "/renders"];
const proxy = Object.fromEntries(routes.map((p) => [p, { target: backend, changeOrigin: true }]));

export default defineConfig({
  plugins: [react()],
  server: { port: 5174, proxy },
});

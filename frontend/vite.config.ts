import path from "path"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"
import type { ProxyOptions } from 'vite'
import sourceIdentifierPlugin from 'vite-plugin-source-identifier'

const isProd = process.env.BUILD_MODE === 'prod'

// API 代理配置：开发环境下将 /api 请求转发到后端
const proxy: Record<string, string | ProxyOptions> = isProd
  ? {}
  : {
      // /api 路径代理到 FastAPI 后端（避免 CORS 问题）
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        // 保留原路径（/api → /api）
        rewrite: (p) => p,
      },
      // /uploads 代理（便于预览分离后的音频轨）
      '/uploads': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (p) => p,
      },
    }

export default defineConfig({
  plugins: [
    react(),
    sourceIdentifierPlugin({
      enabled: !isProd,
      attributePrefix: 'data-matrix',
      includeProps: true,
    })
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    proxy,
  },
  build: {
    outDir: 'dist',
    sourcemap: !isProd,
  },
})

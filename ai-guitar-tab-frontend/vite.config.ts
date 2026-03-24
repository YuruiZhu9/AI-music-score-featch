import path from "path"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"
import sourceIdentifierPlugin from "vite-plugin-source-identifier"

const repoName = "AI-music-score-featch"   // GitHub repo 名称
const isProd  = process.env.BUILD_MODE === "prod"

export default defineConfig({
  // GitHub Pages 部署在 /repo-name/ 子路径
  base: isProd ? `/${repoName}/` : "/",

  plugins: [
    react(),
    sourceIdentifierPlugin({
      enabled: !isProd,
      attributePrefix: "data-matrix",
      includeProps: true,
    }),
  ],

  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },

  build: {
    // 解决多页应用路由问题
    outDir: "dist",
    assetsDir: "assets",
    // 避免过长路径名
    rollupOptions: {
      output: {
        manualChunks: undefined,
      },
    },
  },

  server: {
    // 开发时代理 API 请求到后端，避免 CORS
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
})

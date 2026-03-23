#!/bin/bash
# .devcontainer/setup.sh — AI Guitar Tab 开发环境初始化
set -e

echo "🎸 AI Guitar Tab 开发环境初始化..."

# ── 后端依赖 ──────────────────────────────────────────────
echo "📦 安装后端 Python 依赖..."
cd /workspace/AI-music-score-featch/backend
pip install -r requirements.txt --quiet
echo "✅ 后端依赖安装完成"

# ── 前端依赖 ──────────────────────────────────────────────
echo "📦 安装前端 Node 依赖..."
cd /workspace/AI-music-score-featch/ai-guitar-tab-frontend
npm install
echo "✅ 前端依赖安装完成"

# ── 验证 ─────────────────────────────────────────────────
echo ""
echo "✅ 环境就绪！"
echo "   后端: python backend/main.py"
echo "   前端: cd ai-guitar-tab-frontend && npm run dev"

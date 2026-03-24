# Railway 部署指南

> 本指南详细说明如何将 AI Guitar Tab Transcriber 后端部署到 [Railway](https://railway.app)，免费额度足够个人使用。

---

## 📋 部署前准备

### 账号准备
1. 访问 [railway.app](https://railway.app)，使用 GitHub 账号登录
2. 免费额度：每月 $5，可运行 1 个小项目（完全够用）
3. 信用卡/借记卡验证（必须的，但不收费）

---

## 🚀 方式一：从 GitHub 一键部署（推荐）

### Step 1：创建新项目

1. 登录 Railway → 点击 **"New Project"**
2. 选择 **"Deploy from GitHub repo"**
3. 授权 GitHub 访问，找到 `YuruiZhu9/AI-music-score-featch` 仓库
4. Railway 会自动检测为 **Python** 项目

### Step 2：配置项目

Railway 会自动创建以下内容（可在项目设置中修改）：

| 设置项 | 值 |
|--------|----|
| **Build Command** | `pip install -r backend/requirements.txt` |
| **Start Command** | `uvicorn backend.main:app --host 0.0.0.0 --port $PORT` |
| **Root Directory** | `AI-music-score-featch` |

> ⚠️ `$PORT` 是 Railway 自动注入的环境变量，不要硬写端口号

### Step 3：添加环境变量

在 Railway 项目面板 → **Variables** → 添加：

```env
DEMO_MODE=0
UPLOAD_DIR=/data/uploads
OUTPUT_DIR=/data/outputs
MAX_FILE_SIZE_MB=50
ENVIRONMENT=production
```

### Step 4：添加持久化存储（重要！）

Railway 免费实例的文件系统在重启后会清空，需要挂载持久化存储：

1. 项目面板 → **Storage** → **Add Persistent Disk**
2. 挂载路径：`/data`（Railway 会自动映射到容器内路径）
3. 这样 `uploads/` 和 `outputs/` 的文件就不会丢失

### Step 5：等待部署完成

Railway 会自动：
- 克隆 GitHub 仓库
- 安装 Python 依赖
- 启动 FastAPI 服务

部署完成后，Railway 会给你一个 URL，例如：
```
https://guitar-tab-backend.up.railway.app
```

---

## 🚀 方式二：手动上传 ZIP（不推荐）

如果没有连接 GitHub，可以手动打包上传：

```bash
cd AI-music-score-featch
zip -r backend.zip backend/ -x "*.pyc" -x "__pycache__/*"
```

然后在 Railway 上传 ZIP，配置同上。

---

## 🌐 配置前端连接后端

### 获取后端 URL

Railway 部署完成后，在项目主页复制 URL：
```
https://guitar-tab-backend.up.railway.app
```

### 更新前端环境变量

在 `ai-guitar-tab-frontend/.env.production` 中：

```env
VITE_API_BASE_URL=https://guitar-tab-backend.up.railway.app
```

然后重新构建并推送，前端会自动更新。

### 验证后端是否正常

访问：
```
https://guitar-tab-backend.up.railway.app/docs
```
应该能看到 FastAPI 自动生成的 Swagger 文档页面。

---

## ⚠️ 常见问题

### 1. 部署失败：找不到 `uvicorn`

确保 **Start Command** 正确填写了完整路径（从项目根目录）：

```bash
uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

或者先进入 backend 目录：

```bash
cd AI-music-score-featch/backend && uvicorn main:app --host 0.0.0.0 --port $PORT
```

Railway 的 **Root Directory** 设置为 `AI-music-score-featch`（项目根目录）即可。

### 2. 文件上传 500 错误

检查环境变量是否设置了：

```env
UPLOAD_DIR=/data/uploads
OUTPUT_DIR=/data/outputs
```

并且已挂载持久化存储到 `/data`。

### 3. B站视频下载失败

B站需要登录态 Cookie，在 Railway 环境变量中添加：

```env
BILIBILI_SESSDATA=你的SESSDATA值
```

获取方式：
1. 登录 B站
2. 打开开发者工具 → Application → Cookies → 找到 `SESSDATA`
3. 复制值填入 Railway

> 没有 Cookie 时，yt-dlp 会自动降级，不报错但可能下载失败

### 4. 内存不足（OOM）

Railway 免费版内存有限（512MB）。如果遇到：
```
Killed - memory limit exceeded
```

解决思路：
- 上传文件大小限制在 20MB 以内（`MAX_FILE_SIZE_MB=20`）
- 不安装 GPU 依赖（torch / demucs / crepe），使用纯 CPU Demo 模式
- 只安装核心依赖：`pip install -r backend/requirements.txt`（不要装 GPU 相关）

### 5. 冷启动超时

Railway 免费版有 30s 冷启动限制。服务启动后 Railway 会健康检查 `/health` 端点。

确认 `backend/main.py` 中已有健康检查端点（已内置）：

```
https://guitar-tab-backend.up.railway.app/health
```

应返回 `{"status": "ok"}`。

---

## 💰 成本估算

| 资源 | 免费额度 | 本项目使用 |
|------|---------|-----------|
| CPU 时间 | $5/月 | ≈ 0.5 CPU 核心 |
| 内存 | 512MB | ≈ 300MB |
| 磁盘 | 1GB | < 100MB |
| 带宽 | 100GB/月 | 个人使用足够 |

> 如果月用量超过 $5，Railway 会停止服务但不会收费。

---

## 🔄 更新部署（自动）

连接 GitHub 后，每次推送 `main` 分支，Railway 会**自动重新部署**，无需手动操作。

---

## 🆘 回滚

Railway 支持一键回滚到任意历史版本：

1. 项目主页 → **Deployments**
2. 找到任意历史版本 → 点击 **"Rollback"**

---

*本指南由 小M AI助手 编写 | 2026-03-25*

# AI Guitar Tab Transcriber 🎸

> **目标**：输入音频或视频 URL，自动扒取 **Guitar + Bass 双轨吉他谱**，导出 GTA / PDF / MIDI 文件

---

## 🎯 当前状态：Guitar + Bass 双轨 MVP

**已实现功能：**
- ✅ 上传 MP3 / WAV / FLAC / MP4 音频
- ✅ 粘贴 YouTube / B站 / 抖音 等视频链接（自动下载+提取音频）
- ✅ Guitar 和弦识别（BPM + 时间轴）
- ✅ **Bass 音符识别**（低频音高检测 + 根音推断）
- ✅ **Guitar + Bass 双轨 GTA 文本谱**（ASCII 六线谱）
- ✅ **Guitar + Bass 双轨 MIDI**（可直接导入 Guitar Pro / DAW）
- ✅ PDF 乐谱导出
- ✅ Web 前端（上传 / 进度条 / 结果展示 / 导出下载）
- ⚠️ GPU 模式（Demucs 音频分离 + CREPE 音高检测）需自行安装 torch
- 🔄 Guitar Pro .gp5 文件（底层 MIDI 导入已支持，GP5 二进制格式暂无可靠 Python 库）

**技术方案：**
- Guitar：librosa 和弦识别 + 降级 Demo 模式
- Bass：librosa 低频音高检测（Bass range E1~C4）+ root note 推断
- 音频分离：Demucs（GPU）或原文件 fallback（CPU）
- MIDI：mido 生成双轨 MIDI（Guitar 音色 + Bass 音色）

---

## 🚀 快速开始

### 1. 启动后端

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 2. 启动前端（开发模式）

```bash
cd ai-guitar-tab-frontend
pnpm install
pnpm dev
# 访问 http://localhost:5173
```

### 3. GPU 加速（可选）

```bash
# 安装 PyTorch + Demucs + CREPE
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install demucs crepe
```

### 4. 直接用 Docker（推荐用于测试）

```bash
docker build -t guitar-tab .
docker run -p 8000:8000 -p 5173:5173 guitar-tab
```

---

## 🏗 系统架构

```
┌─────────────────────┐      ┌──────────────────┐
│  Web 前端 (React)   │─────▶│  FastAPI 后端      │
│  localhost:5173     │      │  localhost:8000    │
└─────────────────────┘      └────────┬──────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    ▼                ▼                ▼
              ┌──────────┐  ┌────────────┐  ┌──────────────┐
              │ librosa  │  │  Demucs    │  │   yt-dlp     │
              │ BPM检测  │  │ 音频分离   │  │ 视频下载     │
              │ 和弦识别 │  │ (GPU/CPU)  │  │ B站/YouTube  │
              └────┬─────┘  └─────┬──────┘  └──────────────┘
                   │              │
         ┌─────────┴──────────────┴─────────┐
         ▼                                  ▼
  ┌─────────────┐              ┌──────────────────────┐
  │ Guitar 音高 │              │  Bass 音高检测        │
  │ + 和弦      │              │  (E1~C4 低频范围)     │
  └──────┬──────┘              └──────────┬───────────┘
         │                                 │
         └──────────────┬──────────────────┘
                        ▼
              ┌─────────────────────┐
              │  双轨乐谱生成        │
              │  GTA / PDF / MIDI   │
              │  (Guitar + Bass)    │
              └─────────────────────┘
```

---

## 📁 项目结构

```
AI-music-score-featch/
├── backend/
│   ├── main.py              # FastAPI 入口
│   ├── core/
│   │   ├── pipeline.py      # 主处理流水线（Guitar + Bass）
│   │   ├── separator.py     # Demucs 音频分离
│   │   ├── pitch_detector.py # CREPE / librosa 音高检测
│   │   │                     #   └─ detect_bass_pitch() Bass 专用
│   │   ├── chord_recognizer.py # 和弦识别 + Bass 根音推断
│   │   │                     #   └─ recognize_bass_notes()
│   │   ├── bpm_detector.py   # BPM 节拍检测
│   │   ├── score_generator.py # GTA/PDF/MIDI 生成（双轨）
│   │   │                     #   ├─ Guitar 6弦 TAB
│   │   │                     #   └─ Bass 4弦 TAB
│   │   └── downloader.py    # yt-dlp 视频下载
│   └── models/schemas.py    # Pydantic 数据模型
├── ai-guitar-tab-frontend/  # React + TypeScript + TailwindCSS
│   └── src/
│       ├── pages/Home.tsx   # 上传页面
│       ├── pages/Result.tsx # 结果展示（Guitar + Bass）
│       └── components/       # ChordViewer / GTAViewer / BassViewer
├── .github/workflows/ci.yml # CI/CD（GitHub Pages 部署前端）
└── tests/                   # pytest 单元测试
```

---

## 🌐 部署

### 前端 → GitHub Pages（自动）

推送 `main` 分支后，GitHub Actions 自动构建并部署到：
```
https://YuruiZhu9.github.io/AI-music-score-featch/
```

### 后端 → Railway

详细部署指南见：[DEPLOY-RAILWAY.md](./DEPLOY-RAILWAY.md)

**核心步骤（5分钟完成）：**

1. [railway.app](https://railway.app) → New Project → Deploy from GitHub → 选择本仓库
2. Start Command：`uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
3. 添加环境变量：`DEMO_MODE=0` / `UPLOAD_DIR=/data/uploads` / `OUTPUT_DIR=/data/outputs`
4. 挂载持久化存储到 `/data`（防止重启丢文件）
5. 将 Railway 给你的 URL 填入前端 `.env.production` → `VITE_API_BASE_URL=https://xxx.railway.app`

> 💡 详细说明（含常见问题 / B站Cookie配置 / 内存优化）：[DEPLOY-RAILWAY.md](./DEPLOY-RAILWAY.md)

---

## Vibe Coding 开发流程

本项目采用 **Vibe Coding** 开发流程，严格按以下六个阶段推进：

```
① 需求分析  →  ② 架构设计  →  ③ 功能设计  →  ④ 任务规划  →  ⑤ 任务实现  →  ⑥ 测试验证
```

### ① 需求分析（PRD.md）
- 用户是谁？核心痛点是什么？
- MVP 功能范围是什么？
- 输出：用户故事 + 功能优先级矩阵

### ② 架构设计（ARCHITECTURE.md）
- 系统分成哪几层？
- 技术栈选型是什么？
- API 如何设计？
- 输出：系统架构图 + 模块职责定义

### ③ 功能设计（FUNCTIONAL_DESIGN.md）
- 每个功能的具体交互是什么？
- 页面如何布局？
- 异常情况如何处理？
- 输出：功能规格说明书

### ④ 任务规划（TASK_PLAN.md）
- 每天做什么？
- 提交节奏是什么？
- 如何分配到两个每日开发批次（14:00 / 16:30）？
- 输出：Sprint 任务分配表 + Commit 规范

### ⑤ 任务实现
- 按 TASK_PLAN.md 执行编码
- 每完成一个模块立即 GitHub 提交
- 有阻碍用 Mock/Fallback 绕过

### ⑥ 测试验证
- 单元测试（pytest）
- 端到端集成测试
- 人工验收（Guitar Pro 软件打开文件）

### AI Coding 协作者原则（本项目所有 AI Coding Agent 均须遵守）

> **核心原则：AI 是执行者，不是决策者。所有变更必须经过人类审核才能合并。**

1. **PR 驱动开发**：不直接提交到 main，所有代码变更通过 Pull Request 提交
2. **详细审核**：PR 必须包含变更说明、测试截图/日志、风险评估
3. **安全第一**：检查是否有安全威胁（SQL注入、路径穿越、敏感信息暴露等），有则立即拒绝
4. **破坏性变更需警告**：任何删除文件、删除功能、改变 API 兼容性的变更，必须在 PR 标题注明 `[BREAKING]`
5. **最小化变更**：一个 PR 只做一件事，避免大而全的"超级 PR"
6. **可逆性优先**：优先使用 additive 方式（新增文件/函数），谨慎删除
7. **测试要求**：功能变更必须附带测试，修复必须说明修复了什么 bug
8. **少合并多拒绝**：宁可少合并一个功能，也不能引入一个隐患。对不确定的变更，回复 "需要人工审核" 并列出具体疑问

---

## 技术栈

### 后端（Python）
| 模块 | 技术选型 | 依据 |
|------|---------|------|
| Web 框架 | FastAPI | 高性能、自动API文档、异步 |
| 音频分离 | Demucs（Meta开源） | SOTA开源分离模型，4轨分离 |
| 音高检测 | CREPE（深度学习） | 高精度基频检测，学术SOTA |
| 和弦识别 | librosa chroma | 成熟开源，80%+准确率 |
| 节拍检测 | librosa beat | 成熟开源，误差<1% |
| 乐谱生成 | music21 + guitarpro | 五线谱 + GuitarPro 文件输出 |
| 视频下载 | yt-dlp | 支持B站/YouTube等100+平台 |

### 前端（React）
- React + TypeScript + TailwindCSS
- Vite 构建工具
- 原生 Fetch API（无额外 HTTP 依赖）

### 部署
- 开发：GitHub Codespaces
- 生产：GPU 云服务器（Demucs/CREPE 需要 GPU）

---

### 核心功能

| 功能 | 状态 | 说明 |
|------|------|------|
| 音频文件上传 | ✅ | 支持 MP3/WAV/FLAC/MP4 |
| 视频URL解析 | ✅ | 支持 B站、YouTube 等 |
| 音频分离 | ✅ | Demucs 4轨分离（吉他/鼓/贝斯/人声）|
| BPM/节拍检测 | ✅ | librosa 节拍跟踪 |
| 和弦识别 | ✅ | librosa chroma 色度分析 |
| 音高检测 | ✅ | CREPE 深度学习音高检测 |
| GTA 文本谱生成 | ✅ | ASCII 格式六线谱预览 |
| PDF 乐谱导出 | ✅ | 可打印 PDF |
| Guitar Pro 文件 | ⏳ | MIDI fallback（.gp5 方向推进中）|

---

## 技术架构

```
用户端（浏览器）
    │
    ▼ POST /api/upload
┌─────────────────────────────┐
│    FastAPI 后端（Python）    │
│                              │
│  URL下载/文件上传             │ ← yt-dlp / aiofiles
│        ↓                    │
│  音频分离（Demucs）          │ ← GPU优先，CPU fallback
│        ↓                    │
│  音频分析 Pipeline           │ ← CREPE + librosa
│  - BPM/节拍检测             │
│  - 和弦识别                 │
│  - 音高检测                 │
│        ↓                    │
│  乐谱生成                   │ ← music21 → MIDI
│  - GTA文本谱                │
│  - PDF乐谱                  │
└─────────────────────────────┘
    │
前端预览 ← JSON（和弦+BPM+音符）
    │
    ▼ GET /api/download/{id}
文件下载 ← .gp5 / .pdf / .gta.txt / .mid
```

---

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- ffmpeg（系统依赖）
- GPU（可选，强烈推荐，用于 Demucs/CREPE 加速）

### 后端安装

```bash
cd backend

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .\.venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt

# 启动服务
uvicorn backend.main:app --reload --port 8000
```

### 前端安装

```bash
cd ai-guitar-tab-frontend
npm install       # 或 pnpm install
npm run dev       # 开发模式
npm run build     # 生产构建
```

### 环境变量配置

在 `backend/` 目录创建 `.env` 文件：

```env
# 上传文件大小限制（MB）
MAX_FILE_SIZE_MB=100

# 路径配置（绝对路径或相对路径）
UPLOAD_DIR=./uploads
OUTPUT_DIR=./outputs
MODEL_CACHE_DIR=./model_cache

# 音频处理
SAMPLE_RATE=44100
CREPE_MODEL_CAPACITY=full        # tiny/small/medium/large/full
CREPE_CONFIDENCE_THRESHOLD=0.25

# 音频分离
DEMUCS_MODEL=htdemucs
DEMUCS_DEVICE=auto               # auto/cuda/cpu

# 调试模式
DEBUG=false
```

---

## API 接口

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/` | 服务状态页 |
| GET | `/health` | 健康检查 |
| POST | `/api/upload` | 上传音频文件 |
| POST | `/api/analyze-url` | 分析视频URL |
| GET | `/api/task/{task_id}` | 查询任务状态 |
| GET | `/api/result/{task_id}` | 获取分析结果（JSON） |
| GET | `/api/download/{task_id}` | 下载 Guitar Pro 文件 |
| GET | `/api/download/{task_id}?format=pdf` | 下载 PDF 乐谱 |
| GET | `/api/download/{task_id}?format=gta` | 下载 GTA 文本谱 |

访问 API 文档：`http://localhost:8000/docs`（Swagger UI）

---

## GTA 格式说明

GTA（Guitar Tab ASCII）是文本格式的六线谱，便于快速预览和分享：

```
Song: 晴天
Artist: 周杰伦
Tempo: 128 BPM
Time: 4/4
Capo: 0

e|--0-2-0-3-0-----|---3-1-0-------|
B|-1---3-----3-1---|---------3-1---|
G|--0-2-0-0-0-0---|----------------|
D|--2-0-2-0-0-----|----------------|
A|--3-2-0---------|----------------|
E|--0-------------|----------------|

Chords: Am G C F
```

**标记说明：**
- 数字 = 品位（0=空弦）
- `-` = 休止/空拍
- `h` = 击弦（hammer-on）
- `p` = 勾弦（pull-off）
- `b` = 推弦（bend）
- `/` = 滑音上（slide up）
- `\` = 滑音下（slide down）

---

## 开发指南

### 模块说明

```
backend/
├── main.py                  # FastAPI 入口
├── core/
│   ├── config.py           # 配置管理（Pydantic Settings）
│   ├── pipeline.py         # 主处理流程编排
│   ├── bpm_detector.py     # BPM/节拍检测（librosa）
│   ├── chord_recognizer.py # 和弦识别（librosa chroma）
│   ├── pitch_detector.py   # 音高检测（CREPE）
│   ├── separator.py        # 音频分离（Demucs）
│   ├── score_generator.py  # 乐谱生成（GTA + PDF + MIDI）
│   └── downloader.py       # 视频下载（yt-dlp）
└── models/
    └── schemas.py          # Pydantic 数据模型
```

### 运行测试

```bash
# 单元测试
pytest tests/ -v

# 单模块测试
python -c "from backend.core.bpm_detector import detect_bpm; print('OK')"
```

---

## 项目结构

```
AI-music-score-featch/
├── backend/                    # FastAPI 后端
│   ├── main.py                # 入口
│   ├── core/                  # 核心处理模块
│   ├── models/                # 数据模型
│   ├── api/                   # API 路由
│   ├── utils/                 # 工具函数
│   ├── requirements.txt       # Python 依赖
│   └── .env.example           # 环境变量示例
├── ai-guitar-tab-frontend/    # React 前端
│   ├── src/
│   │   ├── pages/             # 页面组件
│   │   ├── components/        # 可复用组件
│   │   ├── api/              # API 客户端
│   │   └── hooks/            # 自定义 Hooks
│   └── package.json
├── tests/                     # pytest 单元测试
├── .devcontainer/             # GitHub Codespaces 配置
├── .github/workflows/         # GitHub Actions CI/CD
├── PRD.md                     # 需求分析文档
├── ARCHITECTURE.md            # 架构设计文档
├── FUNCTIONAL_DESIGN.md       # 功能设计文档
├── TASK_PLAN.md               # 任务规划
└── README.md                  # 本文档
```

---

## 技术依赖

| 库/框架 | 版本 | 用途 |
|--------|------|------|
| FastAPI | latest | Web 框架 |
| librosa | latest | 音频分析 |
| demucs | latest | 音频分离 |
| CREPE | latest | 音高检测 |
| music21 | latest | 乐谱生成 |
| fpdf2 | latest | PDF 生成 |
| mido | latest | MIDI 文件 |
| yt-dlp | latest | 视频下载 |
| React 18 | latest | 前端框架 |
| Vite | latest | 前端构建 |

---

## 开发路线图

- [x] **M0** 项目骨架 + CI/CD
- [x] **M1** 音频上传 + BPM + 和弦识别
- [x] **M2** 音频分离 + 音高检测
- [x] **M3** GTA 文本谱生成
- [x] **M4** Guitar Pro MIDI fallback
- [ ] **M5** 完整 Web 前端（进行中）
- [ ] **M6** B站/YouTube URL 支持
- [ ] **M7** GPU 优化 + 性能调优

---

## 许可证

GPL-3.0

---

*AI Guitar Tab Transcriber — 用 AI 革新吉他学习体验*

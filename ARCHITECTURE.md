# AI Guitar Tab Transcriber — 架构设计文档

> 版本：v1.0 | 日期：2026-03-23

---

## 一、整体架构

### 1.1 分层架构

```
┌─────────────────────────────────────────────────────┐
│                 前端层 (React SPA)                   │
│   首页/上传 → 进度展示 → 结果预览 → 下载页            │
└──────────────────────────┬──────────────────────────┘
                           │ HTTP/REST (JSON)
┌──────────────────────────▼──────────────────────────┐
│              API 网关层 (FastAPI)                    │
│   /api/upload  /api/task/{id}  /api/result/{id}      │
│   /api/download/{id}   /api/health                   │
└──────────────────────────┬──────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
┌─────────────┐   ┌──────────────┐  ┌──────────────┐
│  任务管理    │   │  音频处理     │  │  文件管理     │
│  (内存/Redis)│   │  Pipeline    │  │  (本地存储)   │
└─────────────┘   └──────────────┘  └──────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
    [yt-dlp]         [Demucs]         [CREPE]
    视频下载           音频分离          音高检测
                                  + librosa
                                  + music21
                                  + guitarpro
```

### 1.2 前后端分离架构

- **前端**：纯静态 Web 应用（Vite + React），可部署在 GitHub Pages
- **后端**：FastAPI + Python，需要运行在有 Python 环境和 GPU 的机器上
- **通信**：REST API，JSON 交换
- **跨域**：开发环境 CORS 全开，生产环境限制来源

---

## 二、模块设计

### 2.1 后端模块

| 模块 | 文件 | 职责 |
|------|------|------|
| **main** | `backend/main.py` | FastAPI 入口、CORS、路由注册 |
| **pipeline** | `backend/core/pipeline.py` | 音频处理主流程编排 |
| **downloader** | `backend/core/downloader.py` | 视频URL下载（yt-dlp） |
| **separator** | `backend/core/separator.py` | Demucs 音频分离 |
| **pitch** | `backend/core/pitch_detector.py` | CREPE 音高检测 |
| **chord** | `backend/core/chord_recognizer.py` | 和弦识别（librosa chroma） |
| **bpm** | `backend/core/bpm_detector.py` | 节拍/BPM 检测 |
| **score_gen** | `backend/core/score_generator.py` | 乐谱生成（music21 → .gp） |
| **models** | `backend/models/schemas.py` | Pydantic 数据模型 |
| **config** | `backend/core/config.py` | 环境变量配置 |

### 2.2 前端模块

| 模块 | 文件 | 职责 |
|------|------|------|
| **App** | `frontend/src/App.tsx` | 路由 + 全局状态 |
| **Home** | `frontend/src/pages/Home.tsx` | 上传页面 |
| **Result** | `frontend/src/pages/Result.tsx` | 结果展示 + 下载 |
| **Uploader** | `frontend/src/components/FileUploader.tsx` | 文件拖拽上传 |
| **Progress** | `frontend/src/components/ProgressBar.tsx` | 处理进度条 |
| **ChordViewer** | `frontend/src/components/ChordViewer.tsx` | 和弦时间轴展示 |
| **GTAViewer** | `frontend/src/components/GTAViewer.tsx` | 文本谱面预览 |
| **api** | `frontend/src/api/client.ts` | Axios API 客户端 |

---

## 三、数据模型

### 3.1 任务状态

```
PENDING → PROCESSING → DONE
                   ↘ ERROR
```

### 3.2 核心数据结构

```python
# 任务记录
TaskRecord:
  task_id: str          # UUID
  status: TaskStatus    # pending/processing/done/error
  progress: float        # 0.0 ~ 1.0
  stage: str             # 当前处理阶段描述
  input_url: str | None  # 视频URL（可选）
  input_path: str | None # 本地文件路径
  result: Result | None  # 最终结果
  created_at: datetime

# 分析结果
Result:
  bpm: int               # 120
  time_signature: str     # "4/4"
  duration_sec: float     # 180.5
  chords: list[Chord]     # 和弦序列
  notes: list[Note]      # 音符序列
  score_files: ScoreFiles # 生成的文件路径

# 和弦事件
Chord:
  start: float   # 秒
  end: float     # 秒
  chord: str     # "Am", "G", "Cmaj7"...

# 音符事件
Note:
  time: float    # 秒
  string: int    # 弦号（1-6）
  fret: int      # 品位（0=空弦）
  duration: str  # "eighth", "quarter"...
```

---

## 四、API 设计

### 4.1 接口清单

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/` | 服务状态页 |
| GET | `/health` | 健康检查 |
| POST | `/api/upload` | 上传音频文件 |
| POST | `/api/analyze-url` | 分析视频URL |
| GET | `/api/task/{task_id}` | 查询任务状态 |
| GET | `/api/result/{task_id}` | 获取分析结果（JSON） |
| GET | `/api/download/{task_id}` | 下载 Guitar Pro 文件 |
| GET | `/api/download/{task_id}/pdf` | 下载 PDF 乐谱 |
| GET | `/api/download/{task_id}/gta` | 下载 GTA 文本谱 |

### 4.2 API 响应格式

```json
// POST /api/upload 响应
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "文件已上传，扒谱任务已启动",
  "poll_url": "/api/task/550e8400-e29b-41d4-a716-446655440000"
}

// GET /api/task/{id} 响应
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "progress": 0.65,
  "stage": "正在识别和弦..."
}

// GET /api/result/{id} 响应
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "bpm": 120,
  "time_signature": "4/4",
  "chords": [
    {"start": 0.0, "end": 1.92, "chord": "Am"},
    {"start": 1.92, "end": 3.84, "chord": "G"}
  ],
  "gta_text": "e|--0-2-0-3-0---|\n..."
}
```

---

## 五、部署架构

### 5.1 开发环境（GitHub Codespaces）

```
GitHub Codespaces (Ubuntu, 4核8G, 无GPU)
  ├── FastAPI 后端 (localhost:8000)
  │     └── Python 3.11 + pip install
  └── Vite 前端 (localhost:5173)
        └── npm install + npm run dev
  访问：通过 Codespaces 端口转发
```

### 5.2 生产环境（推荐）

```
用户请求
    ↓
Cloudflare / Nginx (HTTPS, 反向代理)
    ↓
FastAPI 后端 (云服务器 GPU: A10/T4)
    │
    ├── Demucs (GPU 推理)
    ├── CREPE (GPU 推理)
    └── FastAPI (ASGI, Uvicorn)
    ↓
NFS / MinIO (文件存储)
```

---

## 六、技术决策（ADR）

| # | 决策 | 理由 |
|---|------|------|
| ADR-1 | 用 FastAPI 不用 Flask | 自动API文档、类型安全、异步支持 |
| ADR-2 | 用 Demucs 不用 Spleeter | Demucs v4 分离质量更高，开源维护活跃 |
| ADR-3 | 前端纯 React SPA | 零后端渲染，部署简单 |
| ADR-4 | 用 music21 生成乐谱 | 成熟开源，支持 MusicXML 输出 |
| ADR-5 | GTA 文本先行 | MVP 阶段先输出文本谱，快速验证 |

---

*架构设计：小M AI助手 | 版本：v1.0*

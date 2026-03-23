# AI Guitar Tab Transcriber — 产品规格说明书

> 版本：v0.1.0 MVP
> 依据：AI扒谱商机分析报告（/workspace/reports/ai-music-biz/）
> 目标用户：中国吉他/贝斯翻奏爱好者

---

## 一、核心功能

### MVP 功能范围（v0.1）

| 功能 | 描述 | 优先级 |
|------|------|--------|
| 音频上传 | 支持 MP3 / WAV / FLAC / MP4 上传 | P0 |
| BPM 检测 | 自动识别歌曲节拍速度（精度 < 1%） | P0 |
| 和弦识别 | 识别 700+ 和弦类型，准确率 70-80% | P0 |
| 六线谱生成 | 输出吉他六线谱（支持 Guitar Pro 格式） | P0 |
| 在线预览 | Web 端直接预览谱面 | P0 |
| 音轨分离 | 分离人声/吉他/鼓/贝斯（基于 Demucs） | P1 |
| PDF 导出 | 导出可打印的 PDF 乐谱 | P1 |
| MIDI 导出 | 导出标准 MIDI 文件 | P1 |

### 未来版本（v1.0+）

- 视频转谱（吉他手势识别，差异化核心）
- 智能指法优化（Dijkstra 算法）
- 微信小程序
- 社区 + UGC 曲库

---

## 二、技术架构

### 整体架构

```
┌─────────────────────────────────────────────────┐
│                 前端 (React + Vite)              │
│  上传 → 实时进度 → 谱面预览 → 导出编辑            │
└──────────────────────┬──────────────────────────┘
                       │  HTTP API (REST)
┌──────────────────────▼──────────────────────────┐
│               后端 (FastAPI + Python)            │
│  /upload   /analyze   /chords   /export         │
└──────┬──────────────┬───────────────┬───────────┘
       │              │               │
       ▼              ▼               ▼
  ┌─────────┐   ┌───────────┐   ┌──────────┐
  │Demucs   │   │CREPE      │   │Omnizart  │
  │(分离)   │   │(音高检测)  │   │(和弦识别) │
  └─────────┘   └───────────┘   └──────────┘
       │              │               │
       └──────────────┴───────────────┘
                      │
                     ▼
              ┌──────────────┐
              │ music21      │
              │ lilypond     │
              │ (谱面生成)    │
              └──────────────┘
```

### 技术栈

| 层级 | 技术选型 | 理由 |
|------|---------|------|
| 后端框架 | FastAPI | 高性能、自动化 API 文档、异步支持 |
| 音频分离 | Demucs（Meta 开源） | 5 轨道分离，SOTA 开源方案 |
| 音高检测 | CREPE（深度学习） | 高精度基频检测 |
| 和弦识别 | Omnizart | 专注吉他/和弦识别 |
| 乐谱生成 | music21 + lilypond | 成熟开源乐谱库 |
| 任务队列 | Celery + Redis | 长音频异步处理 |
| 数据库 | SQLite（MVP）/ PostgreSQL（生产） | 轻量、零配置 |
| 存储 | 本地文件系统（MVP）/ MinIO（生产） | 文件临时存储 |
| 前端 | React + TypeScript + TailwindCSS | 现代主流 |

---

## 三、数据流

### 音频 → 谱子 Pipeline

```
用户上传音频 (MP3/WAV)
    │
    ▼
[Step 1] Demucs 音频分离
    ├─ 吉他轨
    ├─ 贝斯轨
    ├─ 鼓轨
    └─ 人声轨
    │
    ▼
[Step 2] CREPE 音高检测
    → 音符时间序列 + 基频
    │
    ▼
[Step 3] Omnizart 和弦识别
    → Chord Timeline (起始时间, 结束时间, 和弦类型)
    │
    ▼
[Step 4] BPM + 节拍检测 (librosa)
    → BPM / 时间签名
    │
    ▼
[Step 5] 乐谱生成 (music21)
    → 五线谱 / 六线谱 / MIDI
    │
    ▼
[Step 6] 导出
    → Guitar Pro (.gp) / PDF / MIDI / 图片
```

---

## 四、API 设计

### 端点

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/upload` | 上传音频文件，返回 `task_id` |
| GET | `/api/task/{task_id}` | 查询处理状态 |
| GET | `/api/result/{task_id}` | 获取分析结果（和弦/BPM/音符） |
| GET | `/api/score/{task_id}` | 获取乐谱文件（PDF/MIDI/GP） |
| GET | `/api/separate/{task_id}` | 获取分离后的音轨 |

### 响应格式

```json
{
  "task_id": "uuid",
  "status": "processing|done|error",
  "progress": 0.65,
  "result": {
    "bpm": 120,
    "time_signature": "4/4",
    "chords": [
      {"start": 0.0, "end": 1.92, "chord": "Am"},
      {"start": 1.92, "end": 3.84, "chord": "G"}
    ],
    "segments": [...]
  }
}
```

---

## 五、用户体验

### 核心使用流程

```
首页
  │
  ▼
拖拽上传音频（支持 B站/YouTube 链接粘贴）★
  │
  ▼
选择乐器：吉他 / 贝斯 / 鼓 / 键盘
  │
  ▼
[处理中] 实时进度条 + 处理阶段说明
  ├─ 正在分离音轨...
  ├─ 正在识别和弦...
  └─ 正在生成乐谱...
  │
  ▼
结果预览页面
  ├─ 和弦时间轴（可播放预览）
  ├─ 六线谱预览
  └─ 标注错误/修正工具
  │
  ▼
导出：PDF / Guitar Pro / MIDI / 图片
```

★ B站/YouTube 链接（未来 v1.0）

---

## 六、项目结构

```
AI-music-score-featch/
├── backend/
│   ├── main.py              # FastAPI 入口
│   ├── api/
│   │   ├── upload.py        # 上传接口
│   │   ├── analyze.py        # 分析接口
│   │   └── export.py         # 导出接口
│   ├── core/
│   │   ├── pipeline.py        # 音频处理 pipeline
│   │   ├── separator.py       # Demucs 音频分离
│   │   ├── pitch_detector.py  # CREPE 音高检测
│   │   ├── chord_recognizer.py # Omnizart 和弦识别
│   │   └── score_generator.py # music21 乐谱生成
│   ├── models/
│   │   └── schemas.py         # Pydantic 数据模型
│   ├── utils/
│   │   └── tasks.py           # Celery 异步任务
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── pages/
│   │   │   ├── Home.tsx       # 上传页面
│   │   │   └── Result.tsx     # 结果预览
│   │   ├── components/
│   │   │   ├── FileUploader.tsx
│   │   │   ├── ChordTimeline.tsx
│   │   │   ├── ScoreViewer.tsx
│   │   │   └── ProgressBar.tsx
│   │   └── api/
│   │       └── client.ts      # API 客户端
│   ├── package.json
│   └── vite.config.ts
│
├── SPEC.md                   # 本规格文档
├── README.md
└── .github/
    └── workflows/
        └── ci.yml            # GitHub Actions 自动测试
```

---

## 七、GitHub 提交节奏

| 节奏 | 时间 | 内容 |
|------|------|------|
| 每日提交 | 工作日每天 | 完成功能模块 / Bug 修复 |
| 周里程碑 | 每周五 | Release tag + 功能汇总 |
| 里程碑 v0.1 | 第 1 周末 | 项目骨架 + README + CI |

---

## 八、关键里程碑

| 里程碑 | 目标 | 验收标准 |
|--------|------|---------|
| **M1：骨架** | 项目结构 + CI/CD | 能跑起来，测试通过 |
| **M2：后端 API** | 上传 + 分离 + 和弦识别 | API 返回正确 JSON |
| **M3：前端** | 上传界面 + 结果展示 | 用户能完整走完流程 |
| **M4：乐谱生成** | PDF/Guitar Pro 导出 | 生成可读谱面 |
| **M5：部署** | GitHub Codespaces | 一键在线运行 |

---

*规格说明编写：小M AI助手 | 依据：AI扒谱商机分析报告*

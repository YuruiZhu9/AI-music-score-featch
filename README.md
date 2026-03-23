# AI Guitar Tab Transcriber
# AI 吉他谱自动扒取工具

> 🎸 **目标**：输入一个视频 URL，等待几分钟，下载到一个 `.gp` 文件，在 Guitar Pro 中打开，看到完整的吉他六线谱

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

**参考报告依据**（/workspace/reports/ai-music-biz/AI扒谱/）：
- 技术可行性分析：各层次成熟度评估 ✅
- 竞品调研：差异化策略（视频转谱 vs 纯音频）
- 产品设计：MVP 功能优先级（P0=和弦识别+BPM，P1=吉他谱生成）

### 前端（React）
- React + TypeScript + TailwindCSS
- Vite 构建工具
- Axios API 客户端

### 部署
- 开发：GitHub Codespaces
- 生产：GPU 云服务器（Demucs/CREPE 需要 GPU）

---

## 项目结构

```
AI-music-score-featch/
├── PRD.md                     ← 需求分析报告
├── ARCHITECTURE.md            ← 架构设计文档
├── FUNCTIONAL_DESIGN.md       ← 功能设计文档
├── TASK_PLAN.md               ← 开发任务规划
├── README.md                  ← 本文件
│
├── backend/
│   ├── main.py                # FastAPI 入口
│   ├── requirements.txt      # Python 依赖
│   ├── .env.example           # 环境变量模板
│   │
│   ├── core/                  # 核心音频处理
│   │   ├── pipeline.py        # 主流程编排
│   │   ├── downloader.py      # 视频URL下载（yt-dlp）
│   │   ├── separator.py        # Demucs 音频分离
│   │   ├── pitch_detector.py  # CREPE 音高检测
│   │   ├── chord_recognizer.py # 和弦识别
│   │   ├── bpm_detector.py     # 节拍/BPM检测
│   │   └── score_generator.py  # GTA文本谱 + GP文件生成
│   │
│   ├── models/
│   │   └── schemas.py         # Pydantic 数据模型
│   │
│   └── api/
│       └── endpoints.py       # API 路由
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── pages/
│   │   │   ├── Home.tsx       # 上传页面
│   │   │   └── Result.tsx     # 结果预览
│   │   ├── components/
│   │   │   ├── FileUploader.tsx
│   │   │   ├── ProgressBar.tsx
│   │   │   ├── ChordViewer.tsx
│   │   │   └── GTAViewer.tsx
│   │   └── api/
│   │       └── client.ts
│   └── package.json
│
└── tests/
    ├── test_pipeline.py
    ├── test_bpm_detector.py
    └── test_chord_recognizer.py
```

---

## API 接口

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/health` | 健康检查 |
| POST | `/api/upload` | 上传音频文件 |
| POST | `/api/analyze-url` | 分析视频URL |
| GET | `/api/task/{id}` | 查询任务状态 |
| GET | `/api/result/{id}` | 获取分析结果 |
| GET | `/api/download/{id}` | 下载Guitar Pro文件 |
| GET | `/api/download/{id}/pdf` | 下载PDF乐谱 |
| GET | `/api/download/{id}/gta` | 下载GTA文本谱 |

---

## 开发节奏

- **14:00（北京）**：完成后端模块（pipeline、BPM、乐谱生成、模型层）
- **16:30（北京）**：完成前端界面（上传、进度、结果预览）
- 每天至少 **2 次 GitHub 提交**
- 每次提交后通过钉钉通知

---

## 快速开始

```bash
# 后端
cd backend
pip install -r requirements.txt
python main.py

# 前端
cd frontend
npm install
npm run dev
```

---

## 核心输出格式：GTA（Guitar Tab ASCII）

项目最终输出 GTA 格式吉他谱示例：

```
Song: 晴天
Artist: 周杰伦
Tempo: 128 BPM
Capo: 0

e|--0-2-0-3-0---||---3-1-0-------|
B|-1---3-----3-1-||---------3-1-|
G|--0-2-0-0-0-0-||----------------|
D|--2-0-2-0-0---||----------------|
A|--3-2-0-------||----------------|
E|--0-----------||----------------|
```

---

*项目启动：2026-03-23 | 开发者：AI Guitar Tab Dev Agent + 小M AI助手*

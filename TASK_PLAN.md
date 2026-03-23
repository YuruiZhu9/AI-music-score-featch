# AI Guitar Tab Transcriber — 任务规划（Vibe Coding 版）

> 版本：v2.0 | 更新：2026-03-23
> 依据：PRD.md + 商机分析报告 + 技术可行性报告
> Vibe Coding 流程：①需求分析 ②架构设计 ③功能设计 ④任务规划 ⑤任务实现 ⑥测试

---

## 一、技术可行性总结（报告核心结论）

| 扒谱层次 | 技术成熟度 | 技术方案 | MVP 可用 |
|---------|-----------|---------|---------|
| BPM/节拍检测 | ✅ 成熟 | librosa beat | ✅ |
| 和弦识别 | ✅ 比较成熟 | librosa chroma | ✅ |
| 音频分离 | ✅ 成熟 | Demucs（4轨） | ✅ |
| 主旋律/音高检测 | ⚠️ 基本可用 | CREPE / librosa pyin | ✅ |
| 鼓组识别 | ⚠️ 基本可用 | Demucs 分离后检测 | ✅ |
| 吉他指法推理 | ❌ 难点 | 暂无成熟方案 | ❌（用和弦+音符代替）|
| 视频手指识别 | ❌ 未成熟 | 长期预研方向 | ❌ |

**MVP 策略**：先做音频版（和弦+BPM+音符），暂不做吉他指法推理，视频转谱 v1.0 搁置。

---

## 二、里程碑（基于报告的竞品差异化策略）

| 里程碑 | 内容 | 验收标准 | 报告依据 |
|--------|------|---------|---------|
| **M0** | 项目骨架 + CI/CD | 能跑、能测试 | 竞品对比基准 |
| **M1** | 音频上传 + BPM + 和弦识别 | API 返回 JSON | Chord AI 80% 准确率 |
| **M2** | 音频分离 + 音高检测 | 分离出吉他/鼓轨 | Demucs SOTA |
| **M3** | GTA 文本谱生成 | 下载 .txt 文件 | GTA 格式规范 |
| **M4** | Guitar Pro 文件生成 | GP7 能打开 | 核心差异化 |
| **M5** | 完整 Web 前端 | 用户走完流程 | Audio Jam UX 参考 |
| **M6** | B站/YouTube URL 支持 | URL → 下载 → 出谱 | 竞品无此功能 |
| **M7** | GPU 优化 + 性能调优 | 处理时间 < 3 分钟 | 技术难点-效率 |

---

## 三、每日开发任务（Vibe Coding 批次）

### Day 1 ✅（已完成）
- [x] 需求分析（PRD.md）
- [x] 架构设计（ARCHITECTURE.md）
- [x] 功能设计（FUNCTIONAL_DESIGN.md）
- [x] 任务规划（本文档）
- [x] Vibe Coding README
- [x] 后端骨架：pipeline / separator / pitch / chord
- [x] 推送到 GitHub ✅

---

### Day 2 → 14:00 批次

**目标：完成后端核心处理层**

- [ ] `backend/core/bpm_detector.py` — librosa 节拍/BPM 检测（成熟技术，直接实现）
- [ ] `backend/core/score_generator.py` — GTA 文本谱生成 + PDF 导出
- [ ] `backend/models/schemas.py` — Pydantic 数据模型（TaskRecord/AnalysisResult/Chord/Note）
- [ ] `backend/core/config.py` — 环境变量配置
- [ ] `README.md` — 环境搭建说明

**技术说明**：
- BPM 检测用 `librosa.beat.beat_track()`，成熟稳定
- GTA 生成：把 Chord timeline + BPM → ASCII 格式文本
- PDF 用 `reportlab` 或 `weasyprint`

---

### Day 2 → 16:30 批次

**目标：前端初始化 + 核心 UI**

- [ ] 前端项目初始化（`init_react_project` 工具）
- [ ] `pages/Home.tsx` — 上传页面（文件上传 + URL 粘贴两个入口）
- [ ] `components/FileUploader.tsx` — 拖拽上传组件
- [ ] `components/ProgressBar.tsx` — 实时进度条（轮询 `/api/task/{id}`）
- [ ] `api/client.ts` — Axios API 客户端封装
- [ ] 前端 `npm install && npm run build` 验证

**前端参考**：Audio Jam 的进度条设计（清晰展示每个处理阶段）

---

### Day 3 → 14:00 批次

**目标：音频处理 Pipeline 集成**

- [ ] 完整 `pipeline.py` 整合所有模块（分离→BPM→和弦→音高→乐谱）
- [ ] `/api/upload` + `/api/analyze-url` 两个入口
- [ ] `backend/main.py` 完善（加入所有路由）
- [ ] 简单 pytest 单元测试（`tests/test_bpm.py`）
- [ ] 用一首 MP3 测试完整流程

**⚠️ 注意事项**：如果 CREPE/Demucs 未安装，所有模块必须有 Mock fallback 返回

---

### Day 3 → 16:30 批次

**目标：Guitar Pro 文件生成 + 结果页**

- [ ] `backend/core/score_generator.py` Guitar Pro 文件输出
  - music21 生成 MusicXML
  - GuitarPro Python 库生成 .gp5
  - 如果库不可用，用 MIDI 格式替代
- [ ] `pages/Result.tsx` — 结果展示页
- [ ] `components/ChordViewer.tsx` — 和弦时间轴（可点击播放）
- [ ] `components/GTAViewer.tsx` — ASCII 谱面渲染
- [ ] `/api/download/gp` + `/api/download/pdf` + `/api/download/gta` 三个导出端点

---

### Day 4 → 14:00 批次

**目标：视频 URL 支持**

- [ ] `backend/core/downloader.py`（yt-dlp 集成）
- [ ] `/api/analyze-url` 端点（解析 B站/YouTube URL）
- [ ] 前端 URL 输入组件（自动识别平台，显示图标）
- [ ] URL 下载失败时的降级处理

**技术说明**：yt-dlp 可稳定下载 B站（需要 cookies 场景暂不处理）

---

### Day 4 → 16:30 批次

**目标：端到端测试 + Bug 修复**

- [ ] 完整集成测试（上传 MP3 → 下载 GP 文件 → Guitar Pro 打开验证）
- [ ] 处理超时/错误处理完善
- [ ] GitHub Actions CI/CD（自动化测试）
- [ ] GitHub Codespaces 配置（`.devcontainer/`）

---

## 四、技术风险与对策（来自报告）

| 风险 | 级别 | 对策 |
|------|------|------|
| guitarpro Python库不存在 | ⚠️ 中 | 用 MIDI 格式替代，GP 文件后续集成 |
| Demucs GPU 不可用 | ⚠️ 中 | CPU fallback，用 librosa 代替 |
| B站视频下载失败 | ⚠️ 中 | 提示用户使用其他来源；记录失败日志 |
| 和弦识别准确率低 | ⚠️ 中 | MVP 目标 70-75%，允许用户在线修正 |
| 处理速度慢 | 🔴 高 | GPU 部署 + 模型量化；先做 1 分钟采样版 |

---

## 五、提交规范

```
[14:00] feat: 完成后端BPM检测和乐谱生成
[16:30] feat: 完成前端初始化和上传组件
[16:30] feat: 完成GuitarPro文件生成和结果页
```

---

*任务规划（Vibe Coding版）：小M AI助手 | 参考：商机分析报告 + 技术可行性报告*

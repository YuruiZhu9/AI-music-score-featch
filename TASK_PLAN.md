# AI Guitar Tab Transcriber — 任务规划

> 版本：v1.0 | 日期：2026-03-23
> 节奏：每天两次提交（14:00 和 16:30北京时间）
> 开发模式：AI Coding Agent 自动执行

---

## 一、总体开发计划

### 里程碑

| 里程碑 | 目标日期 | 内容 | 验收标准 |
|--------|---------|------|---------|
| **M1：骨架** | Day 1 | 项目结构 + CI/CD + 后端基础API | 服务启动，API可访问 |
| **M2：音频Pipeline** | Day 2 | 完整音频分析流程 | 上传MP3返回JSON |
| **M3：GTA文本谱** | Day 3 | GTA格式生成 | 下载.txt文件 |
| **M4：GuitarPro文件** | Day 4-5 | .gp5文件生成 | Guitar Pro能打开 |
| **M5：前端界面** | Day 6-7 | 完整Web UI | 用户走完全流程 |
| **M6：B站URL支持** | Day 8-9 | 视频URL解析 | 输入B站URL→下载→出谱 |
| **M7：部署上线** | Day 10 | GitHub Codespaces | 一键运行 |

---

## 二、每日任务分配

### Day 1（今天已完成）
- [x] 需求分析（PRD.md）
- [x] 架构设计（ARCHITECTURE.md）
- [x] 功能设计（FUNCTIONAL_DESIGN.md）
- [x] 项目骨架（backend/ 目录）
- [x] GitHub 仓库建立

### Day 2 → 14:00 第一次提交
- [ ] 完成 `backend/core/pipeline.py`（主流程编排）
- [ ] 完成 `backend/core/bpm_detector.py`（节拍检测）
- [ ] 完成 `backend/core/score_generator.py`（乐谱生成）
- [ ] 完成 `backend/models/schemas.py`（Pydantic模型）
- [ ] 编写 README.md（项目说明）
- [ ] **提交 Commit: "feat: 完成后端核心pipeline和BPM检测"**

### Day 2 → 16:30 第二次提交
- [ ] 初始化前端项目（React + Vite + TypeScript）
- [ ] 搭建前端目录结构
- [ ] 完成 `FileUploader` 组件
- [ ] 完成 `ProgressBar` 组件
- [ ] 完成 API 客户端（`api/client.ts`）
- [ ] **提交 Commit: "feat: 前端项目初始化和上传组件"**

### Day 3 → 14:00 第三次提交
- [ ] 完成后端 API 测试（pytest）
- [ ] 完成 `Result` 页面（结果展示）
- [ ] 完成 `ChordViewer` 组件（和弦时间轴）
- [ ] 完成 GTA 文本谱生成逻辑
- [ ] **提交 Commit: "feat: 结果展示页面和GTA文本谱生成"**

### Day 3 → 16:30 第四次提交
- [ ] 完成 GTA Viewer 组件（ASCII谱面渲染）
- [ ] 完成 `/api/download/gta` 端点
- [ ] 完成 PDF 导出功能
- [ ] 完成 Guitar Pro 文件生成
- [ ] **提交 Commit: "feat: 多格式导出（GP/PDF/TXT）"**

### Day 4-5 → 视频URL支持 + 完整测试
- [ ] 完成 `downloader.py`（yt-dlp 集成）
- [ ] 完成 `/api/analyze-url` 端点
- [ ] 完成视频URL前端输入组件
- [ ] 全流程集成测试
- [ ] **提交 Commit: "feat: B站/YouTube URL视频解析"**

---

## 三、提交信息规范

### Commit Message 格式
```
<type>: <简短描述>

<可选的详细说明>

<可选的测试结果>

Types:
  feat:     新功能
  fix:      Bug修复
  docs:     文档更新
  refactor: 代码重构
  test:     测试相关
  chore:    工具/依赖更新

Example:
feat:完成后端核心pipeline和BPM检测

- 完成音频处理主流程编排
- 实现librosa BPM检测
- 添加Pydantic数据模型
- 全部接口返回正确JSON
```

---

## 四、代码规范

### Python（后端）
- 使用 type hints（强制）
- Docstring 格式：Google style
- 行长度：≤120字符
- 格式化：black + isort

### TypeScript（前端）
- 严格模式（strict: true）
- 使用 interface 定义数据模型
- 使用 React Hooks 管理状态
- 样式：TailwindCSS utility classes

---

## 五、测试策略

### 单元测试
- 每个核心模块（separator/pitch/chord/bpm/score）
- 使用 pytest + pytest-asyncio
- Mock Demucs/CREPE 等重型依赖

### 集成测试
- 完整 Pipeline 端到端测试
- 使用 sample audio 文件（< 1MB）

---

*任务规划：小M AI助手 | 版本：v1.0*

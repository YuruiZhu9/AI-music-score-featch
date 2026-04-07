"""
backend/api/routes.py — API 路由文档与路由清单
================================================
列出项目中所有 FastAPI 路由路径、请求/响应格式，方便前端对接与调试。
不包含业务逻辑，仅为文档参考。

路由注册位置：backend/main.py
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class RouteSpec:
    """
    单个 API 路由的元数据规范。

    属性：
        method:     HTTP 方法（GET / POST / PUT / DELETE）
        path:       路由路径
        summary:    简短中文描述
        request:    请求格式（None 表示无需请求体）
        response:   成功响应 schema
        errors:     可能错误码列表
        tag:        OpenAPI tag（分组用）
        notes:      补充说明
    """
    method: str
    path: str
    summary: str
    request: Optional[str] = None
    response: Optional[str] = None
    errors: Optional[List[int]] = None
    tag: str = "通用"
    notes: Optional[str] = None


# ─── 全量路由清单 ─────────────────────────────────────────────────

ROUTES: List[RouteSpec] = [
    # ── 状态 ────────────────────────────────────────────────────────
    RouteSpec(
        method="GET",
        path="/",
        summary="服务状态页",
        response="HTML 页面（服务正常运行）",
        errors=None,
        tag="状态",
        notes="返回前端页面入口，调试用",
    ),
    RouteSpec(
        method="GET",
        path="/health",
        summary="健康检查",
        response='{"status": "ok", "version": "0.4.0", "modules": {...}}',
        errors=None,
        tag="状态",
        notes="检查各依赖模块（librosa、fpdf2、mido、midi）是否可用",
    ),

    # ── 任务管理 ────────────────────────────────────────────────────
    RouteSpec(
        method="POST",
        path="/api/upload",
        summary="上传音频文件并启动扒谱任务",
        request="multipart/form-data: file (音频文件, ≤100MB)",
        response='{"task_id": "uuid", "status": "pending", "poll_url": "/api/task/{task_id}"}',
        errors=[400, 413],
        tag="任务",
        notes="支持 MP3/WAV/FLAC/MP4；返回 task_id 用于后续查询",
    ),
    RouteSpec(
        method="POST",
        path="/api/analyze-url",
        summary="粘贴视频URL，自动下载+扒谱",
        request='{"url": "https://...", "song_name": "歌曲名（可选）"}',
        response='{"task_id": "uuid", "status": "pending", "poll_url": "/api/task/{task_id}"}',
        errors=[400, 422],
        tag="任务",
        notes="支持 B站/YouTube/抖音等；音频自动提取后走同一 pipeline",
    ),
    RouteSpec(
        method="GET",
        path="/api/task/{task_id}",
        summary="轮询任务处理进度",
        response='{"task_id": "uuid", "status": "processing", "progress": 0.65, "stage": "正在识别和弦..."}',
        errors=[404],
        tag="任务",
        notes="前端每 2-3 秒轮询一次，直至 status == done 或 error",
    ),

    # ── 结果查询 ────────────────────────────────────────────────────
    RouteSpec(
        method="GET",
        path="/api/result/{task_id}",
        summary="获取完整分析结果（JSON）",
        response='''{
  "task_id": "uuid",
  "bpm": 128,
  "time_signature": "4/4",
  "duration_sec": 180.5,
  "guitar": {
    "chords": [{"start": 0.0, "end": 1.92, "chord": "Am"}, ...],
    "notes": [{"time": 0.0, "note": "E4", "string": 6, "fret": 0, "confidence": 0.95}, ...]
  },
  "bass": {
    "notes": [{"start": 0.0, "end": 0.5, "note": "A1", "midi": 45, "string": 3, "fret": 0, "confidence": 0.88}],
    "chords": []
  },
  "gta_text": "🎸 Song Title..."
}''',
        errors=[404, 202],
        tag="结果",
        notes="返回 202 表示任务仍在 processing；前端应继续轮询 /api/task/{task_id}",
    ),

    # ── 文件下载 ────────────────────────────────────────────────────
    RouteSpec(
        method="GET",
        path="/api/download/{task_id}",
        summary="下载 Guitar Pro / MIDI 文件",
        response="文件流（Content-Type: audio/midi 或 application/octet-stream）",
        errors=[404],
        tag="下载",
        notes="优先级：Guitar Pro .gp > MIDI .mid；文件名为 {task_id}.mid 或 .gp",
    ),
    RouteSpec(
        method="GET",
        path="/api/download/{task_id}/pdf",
        summary="下载 PDF 乐谱",
        response="文件流（Content-Type: application/pdf）",
        errors=[404],
        tag="下载",
        notes="包含 Guitar + Bass 双轨谱面，Guitar Pro 指法参考页",
    ),
    RouteSpec(
        method="GET",
        path="/api/download/{task_id}/gta",
        summary="下载 GTA 文本谱（ASCII TAB）",
        response="文件流（Content-Type: text/plain; charset=utf-8）",
        errors=[404],
        tag="下载",
        notes="纯文本六线谱，可在任何文本编辑器打开",
    ),
]


# ─── 前端对接要点 ─────────────────────────────────────────────────

FRONTEND_QUICKREF = """
=== 前端对接速查 ===

1. 上传流程：
   POST /api/upload (file) → { task_id }
   → 每3秒轮询 GET /api/task/{task_id}
   → status==done 后 GET /api/result/{task_id}
   → 用户点击下载按钮 → GET /api/download/{task_id}/pdf

2. URL 分析流程：
   POST /api/analyze-url ({"url": "..."})
   → { task_id } → 同上轮询流程

3. 前端轮询建议：
   - 轮询间隔：2-3 秒
   - 进度条：根据 response.progress (0.0~1.0) 更新
   - stage 示例："正在检测 BPM..." / "正在分离音频..." / "正在识别和弦..."
   - 超时：60 秒内未完成应提示用户

4. 文件下载：
   - 使用 <a href="/api/download/{task_id}/pdf" download> 触发下载
   - PDF 文件名：{task_id}.pdf
   - GTA 文件名：{task_id}.gta.txt

5. 错误处理：
   - 404：task_id 不存在或已被清理
   - 413：文件超过 100MB 限制
   - 500：服务端内部错误，提示用户重试
"""

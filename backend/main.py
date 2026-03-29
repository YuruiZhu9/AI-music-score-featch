"""
AI Guitar Tab Transcriber — FastAPI Backend
==========================================
Core entry point for the transcription service.
"""

import os
import uuid
from pathlib import Path
from typing import Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ─── App Lifespan ────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize directories and models on startup."""
    # Ensure upload / output directories exist
    upload_dir = Path(os.getenv("UPLOAD_DIR", "./uploads"))
    output_dir = Path(os.getenv("OUTPUT_DIR", "./outputs"))
    upload_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"✅ AI Guitar Tab Transcriber started")
    print(f"   Upload dir : {upload_dir}")
    print(f"   Output dir: {output_dir}")
    
    yield
    
    print("🛑 Shutting down...")

# ─── FastAPI App ─────────────────────────────────────────────────

app = FastAPI(
    title="AI Guitar Tab Transcriber",
    description="从任意音频自动扒取吉他谱 — MVP",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow frontend during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: restrict to frontend origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── In-memory task registry (use Redis in production) ───────────

from enum import Enum

class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    ERROR = "error"

class TaskRecord(BaseModel):
    task_id: str
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0          # 0.0 – 1.0
    stage: str = "等待上传"
    input_path: str | None = None
    result: dict | None = None
    error: str | None = None

tasks: dict[str, TaskRecord] = {}

# ─── API Routes ──────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "name": "AI Guitar Tab Transcriber",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/api/upload")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    """
    Upload an audio file and start the transcription pipeline.
    
    Returns a task_id that can be used to poll /api/task/{task_id}.
    """
    # ── Validate file type ─────────────────────────────────────
    allowed_types = {
        "audio/mpeg": "mp3",
        "audio/wav": "wav",
        "audio/flac": "flac",
        "audio/x-flac": "flac",
        "video/mp4": "mp4",
        "video/mpeg": "mp3",
        "application/octet-stream": "bin",
    }
    ext = allowed_types.get(file.content_type, None)
    if ext is None:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {file.content_type}。"
                   f"请上传 MP3、WAV、FLAC 或 MP4 文件。",
        )

    # ── Save file to disk ──────────────────────────────────────
    task_id = str(uuid.uuid4())
    upload_dir = Path(os.getenv("UPLOAD_DIR", "./uploads"))
    input_path = upload_dir / f"{task_id}.{ext}"

    content = await file.read()
    max_mb = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
    if len(content) > max_mb * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"文件超过 {max_mb}MB 限制。",
        )

    with open(input_path, "wb") as f:
        f.write(content)

    # ── Register task ───────────────────────────────────────────
    task = TaskRecord(
        task_id=task_id,
        status=TaskStatus.PENDING,
        input_path=str(input_path),
        stage="文件已接收",
    )
    tasks[task_id] = task

    # ── Kick off background processing ─────────────────────────
    from core.pipeline import run_pipeline
    background_tasks.add_task(run_pipeline, task_id, input_path)

    return {
        "task_id": task_id,
        "status": "pending",
        "message": "文件已上传，扒谱任务已启动。",
        "poll_url": f"/api/task/{task_id}",
    }


@app.get("/api/task/{task_id}")
async def get_task_status(task_id: str):
    """Poll task status and progress."""
    task = tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在。")
    return {
        "task_id": task.task_id,
        "status": task.status.value,
        "progress": task.progress,
        "stage": task.stage,
        "error": task.error,
    }


@app.get("/api/result/{task_id}")
async def get_result(task_id: str):
    """
    Retrieve the full transcription result once done.
    返回结构与前端 AnalysisResult 类型对齐：score_files / gta_text 等字段在顶层。
    """
    task = tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在。")
    if task.status == TaskStatus.ERROR:
        raise HTTPException(status_code=500, detail=task.error)
    if task.status != TaskStatus.DONE:
        raise HTTPException(status_code=202, detail="任务尚未完成。")

    # task.result 已包含完整结果结构（pipeline.py 保证）
    result = task.result or {}
    return {
        "task_id": task_id,
        **result,  # score_files / gta_text / guitar / bass 等字段直接展开到顶层
    }


@app.post("/api/analyze-url")
async def analyze_url(
    url: str = Form(..., description="视频/音频 URL，支持 B站、YouTube 等"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """
    分析视频URL：下载视频 → 提取音频 → 开始扒谱 pipeline。
    支持 B站、YouTube 等平台。
    """
    # 验证 URL
    from backend.core.downloader import is_supported_url, get_video_metadata

    if not is_supported_url(url):
        raise HTTPException(
            status_code=400,
            detail="不支持的URL平台。仅支持：B站、YouTube、抖音等主流视频平台。"
        )

    # 获取视频元信息（不阻塞，主要信息在前端展示）
    metadata: dict[str, Any] = {}
    try:
        metadata = get_video_metadata(url) or {}
    except Exception:
        pass  # 元信息获取失败不影响主流程

    # 创建任务
    task_id = str(uuid.uuid4())
    upload_dir = Path(os.getenv("UPLOAD_DIR", "./uploads"))
    upload_dir.mkdir(parents=True, exist_ok=True)

    task = TaskRecord(
        task_id=task_id,
        status=TaskStatus.PENDING,
        stage="正在下载视频...",
    )
    tasks[task_id] = task

    # 启动下载 + 分析 pipeline
    from core.downloader import extract_audio_from_url
    from core.pipeline import run_pipeline

    def _url_pipeline():
        """在后台线程中执行：下载视频 → 提取音频 → 运行 pipeline。"""
        try:
            audio_path = extract_audio_from_url(url, task_id, upload_dir)
            if audio_path and audio_path.exists():
                task.stage = "视频下载完成，开始分析..."
                run_pipeline(task_id, audio_path)
            else:
                task.status = TaskStatus.ERROR
                task.error = "视频下载失败，请检查链接是否有效，或尝试直接上传音频文件。"
                task.stage = "下载失败"
        except Exception as exc:
            task.status = TaskStatus.ERROR
            task.error = f"视频处理出错: {exc}"
            task.stage = "处理失败"

    background_tasks.add_task(_url_pipeline)

    return {
        "task_id": task_id,
        "status": "pending",
        "message": "视频链接已接收，正在下载并分析...",
        "metadata": metadata,
        "poll_url": f"/api/task/{task_id}",
    }


@app.get("/api/download/{task_id}")
async def download_score(task_id: str, format: str = "gta"):
    """
    Download the generated score.
    format: gta (default) | pdf | midi | gp | json
    """
    task = tasks.get(task_id)
    if task is None or task.status != TaskStatus.DONE:
        raise HTTPException(status_code=404, detail="结果不存在。")

    output_dir = Path(os.getenv("OUTPUT_DIR", "./outputs")) / task_id

    # 查找文件（pipeline 保存的命名规则）
    format_map = {
        "gta":  ("score.gta.txt", "text/plain"),
        "pdf":  ("score.pdf",     "application/pdf"),
        "midi": ("score.mid",     "audio/midi"),
        "gp":   ("score.gp5",    "application/octet-stream"),
        "json": (f"{task_id}.json", "application/json"),   # pipeline 保存为 {task_id}.json
    }
    filename, media_type = format_map.get(format, ("score.gta.txt", "text/plain"))
    score_path = output_dir / filename

    if not score_path.exists():
        raise HTTPException(status_code=404, detail=f"找不到 {format} 文件，请先完成分析。")

    return FileResponse(
        score_path,
        media_type=media_type,
        filename=f"tab.{format}",
    )


# ─── Run locally ────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )

"""
AI Guitar Tab Transcriber — FastAPI Backend
==========================================
Core entry point for the transcription service.
"""

import os
import uuid
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
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
    from backend.core.pipeline import run_pipeline
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
    """Retrieve the full transcription result once done."""
    task = tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在。")
    if task.status == TaskStatus.ERROR:
        raise HTTPException(status_code=500, detail=task.error)
    if task.status != TaskStatus.DONE:
        raise HTTPException(status_code=202, detail="任务尚未完成。")
    return {
        "task_id": task_id,
        "result": task.result,
    }


@app.get("/api/download/{task_id}")
async def download_score(task_id: str, format: str = "pdf"):
    """
    Download the generated score.
    format: pdf | midi | gp (guitar pro) | json
    """
    task = tasks.get(task_id)
    if task is None or task.status != TaskStatus.DONE:
        raise HTTPException(status_code=404, detail="结果不存在。")

    output_dir = Path(os.getenv("OUTPUT_DIR", "./outputs"))
    score_path = output_dir / f"{task_id}_score.{format}"

    if not score_path.exists():
        raise HTTPException(status_code=404, detail=f"找不到 {format} 文件。")

    return FileResponse(
        score_path,
        media_type="application/octet-stream",
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

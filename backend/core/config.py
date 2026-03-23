"""
backend/core/config.py — 环境变量配置
======================================
使用 Pydantic Settings 进行配置管理，支持：
- .env 文件自动加载
- 环境变量覆盖
- 类型校验 + 文档

使用方式：
    from backend.core.config import settings
    print(settings.UPLOAD_DIR)
"""

import os
from pathlib import Path
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """
    应用全局配置。
    所有配置项均可通过环境变量覆盖（环境变量优先级高于 .env 文件）。
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,  # 环境变量不区分大小写
        extra="allow",
    )

    # ── 服务基础配置 ────────────────────────────────────────────
    APP_NAME: str       = Field("AI Guitar Tab Transcriber", description="应用名称")
    APP_VERSION: str     = Field("0.1.0", description="版本号")
    DEBUG: bool          = Field(False, description="调试模式")

    # ── 路径配置 ────────────────────────────────────────────────
    # 上传目录：存放用户上传的原始音频/视频
    UPLOAD_DIR: Path = Field(
        Path("./uploads"),
        description="上传文件存储目录（绝对路径或相对路径）",
    )
    # 输出目录：存放处理结果（分离的音轨、乐谱文件）
    OUTPUT_DIR: Path = Field(
        Path("./outputs"),
        description="输出文件存储目录",
    )
    # 模型缓存目录
    MODEL_CACHE_DIR: Path = Field(
        Path("./model_cache"),
        description="预训练模型缓存目录（Demucs、CREPE 等）",
    )

    @field_validator("UPLOAD_DIR", "OUTPUT_DIR", "MODEL_CACHE_DIR", mode="before")
    @classmethod
    def _resolve_path(cls, v) -> Path:
        p = Path(v)
        if not p.is_absolute():
            # 相对于项目根目录（backend/ 的上一级）
            base = Path(__file__).parent.parent.parent
            p = base / v
        p.mkdir(parents=True, exist_ok=True)
        return p.resolve()

    # ── 文件限制 ─────────────────────────────────────────────────
    MAX_FILE_SIZE_MB: int = Field(100, ge=1, le=500, description="上传文件最大大小（MB）")
    ALLOWED_AUDIO_TYPES: List[str] = Field(
        default=[
            "audio/mpeg", "audio/mp3",
            "audio/wav", "audio/x-wav",
            "audio/flac", "audio/x-flac",
            "audio/ogg", "audio/vorbis",
            "video/mp4", "video/webm",
            "application/octet-stream",
        ],
        description="允许上传的 MIME 类型列表",
    )

    # ── 音频处理配置 ─────────────────────────────────────────────
    SAMPLE_RATE: int = Field(44100, description="音频重采样目标采样率（Hz）")
    # BPM 检测配置
    BPM_MIN: int = Field(40,   description="BPM 下限")
    BPM_MAX: int = Field(220,  description="BPM 上限")
    BPM_DEFAULT: int = Field(120, description="BPM 默认值")
    # CREPE 模型容量：tiny / small / medium / large / full
    CREPE_MODEL_CAPACITY: str = Field(
        "full",
        description="CREPE 音高检测模型容量（影响精度和速度）",
    )
    CREPE_CONFIDENCE_THRESHOLD: float = Field(
        0.25,
        ge=0.0, le=1.0,
        description="CREPE 置信度阈值，低于此值的结果被过滤",
    )

    # ── 音频分离配置 ─────────────────────────────────────────────
    # Demucs 模型：htdemucs / htdemucs_ft / htdemucs_6s / mdx_extra
    DEMUCS_MODEL: str = Field(
        "htdemucs",
        description="Demucs 音频分离模型",
    )
    # GPU 设备：cuda / cpu（自动检测时填 auto）
    DEMUCS_DEVICE: str = Field(
        "auto",
        description="Demucs 运行设备（cuda / cpu / auto）",
    )

    # ── 乐谱生成配置 ─────────────────────────────────────────────
    # 每个四分音符在 GTA 中的字符宽度
    GTA_BEAT_WIDTH: int = Field(4, description="GTA 谱每拍字符数（影响密度）")
    MAX_TAB_BARS: int = Field(64, description="GTA 谱最大小节数")
    PDF_ENGINE: str = Field(
        "lilypond",
        description="PDF 生成引擎：lilypond / weasyprint / html",
    )

    # ── CORS 配置 ────────────────────────────────────────────────
    CORS_ORIGINS: List[str] = Field(
        ["*"],
        description="允许的 CORS 来源（生产环境应限制为具体域名）",
    )

    # ── 并发 / 性能配置 ──────────────────────────────────────────
    # 最大并发任务数（超过后排队）
    MAX_CONCURRENT_TASKS: int = Field(3, ge=1, le=20)
    # 单个任务超时（秒）
    TASK_TIMEOUT_SEC: int = Field(600, ge=60, description="任务最大处理时间（秒）")

    # ── API Key 配置（可选）──────────────────────────────────────
    YTDLP_API_KEY: str = Field("", description="yt-dlp 相关 API Key（如需）")

    # ── 存储清理配置 ─────────────────────────────────────────────
    # 任务完成后保留原始文件的时长（秒），0=立即删除
    FILE_RETENTION_SEC: int = Field(3600, description="文件保留时长（秒）")

    def is_audio_allowed(self, mime_type: str) -> bool:
        """检查 MIME 类型是否在允许列表中。"""
        return mime_type in self.ALLOWED_AUDIO_TYPES

    def validate_bpm(self, bpm: float) -> int:
        """修正并验证 BPM 在合理范围内。"""
        bpm = int(round(bpm))
        return max(self.BPM_MIN, min(self.BPM_MAX, bpm))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    获取全局配置单例（使用 lru_cache 缓存，避免重复解析 .env）。
    
    用法：
        from backend.core.config import get_settings
        settings = get_settings()
    """
    return Settings()

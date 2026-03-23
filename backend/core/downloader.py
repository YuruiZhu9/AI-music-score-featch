"""
视频URL下载器 — yt-dlp 集成
===================================
支持 B站、YouTube、抖音等100+平台的视频下载和音频提取。
"""

import os
import logging
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def is_supported_url(url: str) -> bool:
    """检查URL是否为支持的视频平台。"""
    platforms = [
        "bilibili.com",
        "b23.tv",
        "youtube.com",
        "youtu.be",
        "douyin.com",
        "ixigua.com",
        "weibo.com",
    ]
    return any(p in url for p in platforms)


def extract_audio_from_url(url: str, task_id: str, output_dir: Path) -> Optional[Path]:
    """
    从视频URL下载并提取音频。
    
    Returns:
        音频文件路径（MP3/WAV），下载失败返回 None
    """
    try:
        import yt_dlp
    except ImportError:
        logger.warning("yt-dlp 未安装，无法下载视频URL。")
        return None

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{task_id}.mp3"

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": str(output_dir / f"{task_id}.%(ext)s"),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "quiet": True,
        "no_warnings": True,
        # B站需要 headers
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        },
    }

    # B站特殊处理
    if "bilibili.com" in url or "b23.tv" in url:
        ydl_opts["extractor_args"] = {"bilibili": {"cookie": "SESSDATA=needed"}}
        # 如果没有cookie，降级到无cookie模式
        ydl_opts["ignoreerrors"] = True

    try:
        logger.info(f"[{task_id}] 下载视频: {url}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            logger.info(f"[{task_id}] 下载完成: {info.get('title', 'unknown')}")

        # yt-dlp 可能生成不同扩展名，找最新的
        mp3_candidates = list(output_dir.glob(f"{task_id}.*"))
        for candidate in mp3_candidates:
            if candidate.suffix in [".mp3", ".wav", ".m4a", ".flac"]:
                logger.info(f"[{task_id}] 音频文件: {candidate}")
                return candidate

        return output_path if output_path.exists() else None

    except Exception as exc:
        logger.error(f"[{task_id}] 视频下载失败: {exc}")
        return None


def get_video_metadata(url: str) -> Optional[dict]:
    """获取视频元信息（标题、时长、封面）。"""
    try:
        import yt_dlp

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            },
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                "title": info.get("title", "未知标题"),
                "duration": info.get("duration", 0),
                "thumbnail": info.get("thumbnail"),
                "uploader": info.get("uploader", "未知作者"),
            }
    except Exception as exc:
        logger.warning(f"获取视频元信息失败: {exc}")
        return None

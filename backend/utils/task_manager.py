"""
backend/utils/task_manager.py — 任务清理与文件生命周期管理
============================================================
负责定时清理过期任务，释放磁盘空间。
支持：
- 清理超过一定时间的已完成任务文件
- 清理孤立的上传文件
- manifest.json 管理活跃任务列表

用法：
    from backend.utils.task_manager import TaskCleanup
    cleanup = TaskCleanup(output_dir=output_dir, retention_sec=3600)
    removed = cleanup.run()
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


class TaskCleanup:
    """
    任务文件清理器。

    扫描指定目录，删除超过 retention_sec 秒的旧文件，
    同时维护一个 manifest.json 记录活跃任务。

    参数：
        output_dir:     输出目录（含 GTA/PDF/MIDI/JSON 文件）
        upload_dir:     上传目录（原始音频/视频文件）
        retention_sec:  文件保留时长（秒），默认 3600（1小时）
        dry_run:        True=只打印不删除（用于调试）
    """

    # 活跃文件扩展名（这些文件需要检查清理）
    OUTPUT_EXTENSIONS = {".gta.txt", ".pdf", ".mid", ".gp", ".json"}
    UPLOAD_EXTENSIONS = {
        ".mp3", ".wav", ".flac", ".ogg",
        ".mp4", ".webm", ".mkv", ".m4a",
    }

    def __init__(
        self,
        output_dir: Path,
        upload_dir: Path,
        retention_sec: int = 3600,
        dry_run: bool = False,
    ):
        self.output_dir = Path(output_dir)
        self.upload_dir = Path(upload_dir)
        self.retention_sec = retention_sec
        self.dry_run = dry_run
        self._removed: List[str] = []
        self._removed_sizes: List[int] = []  # 被删文件大小（字节），用于统计
        self._errors: List[str] = []

    def run(self) -> Dict[str, List[str]]:
        """
        执行清理，返回清理报告。

        返回：
            {
                "removed": [文件路径列表],
                "errors": [错误信息列表],
                "freed_mb": float,
                "dry_run": bool,
            }
        """
        if not self.dry_run:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            self.upload_dir.mkdir(parents=True, exist_ok=True)

        now = time.time()
        cutoff = now - self.retention_sec

        logger.info(
            f"[TaskCleanup] 启动清理 (retention={self.retention_sec}s, "
            f"cutoff={cutoff:.0f}, dry_run={self.dry_run})"
        )

        # ── 清理输出目录 ──────────────────────────────────────────
        self._clean_directory(self.output_dir, cutoff, self.OUTPUT_EXTENSIONS)

        # ── 清理上传目录 ─────────────────────────────────────────
        self._clean_directory(self.upload_dir, cutoff, self.UPLOAD_EXTENSIONS)

        freed_bytes = sum(self._removed_sizes)
        freed_mb = freed_bytes / (1024 * 1024)

        report = {
            "removed": self._removed,
            "errors": self._errors,
            "freed_mb": round(freed_mb, 2),
            "dry_run": self.dry_run,
        }

        logger.info(
            f"[TaskCleanup] 完成: 清理 {len(self._removed)} 个文件, "
            f"释放 {report['freed_mb']:.1f} MB"
        )
        return report

    def _clean_directory(
        self,
        directory: Path,
        cutoff_timestamp: float,
        extensions: set,
    ) -> None:
        """扫描并清理单个目录中超过阈值的旧文件。"""
        if not directory.exists():
            return

        for file_path in directory.iterdir():
            if not file_path.is_file():
                continue

            # 支持复合扩展名（如 .gta.txt）和普通扩展名
            name_lower = file_path.name.lower()
            ext_ok = any(name_lower.endswith(ext) for ext in extensions)
            if not ext_ok:
                continue

            if file_path.name in ("manifest.json", ".gitkeep"):
                continue

            try:
                mtime = file_path.stat().st_mtime
                if mtime < cutoff_timestamp:
                    size_bytes = file_path.stat().st_size
                    size_mb = size_bytes / (1024 * 1024)
                    if self.dry_run:
                        logger.info(
                            f"[DryRun] 将删除: {file_path} "
                            f"({size_mb:.1f}MB, age={int(time.time()-mtime)}s)"
                        )
                    else:
                        file_path.unlink(missing_ok=True)
                        self._removed.append(str(file_path))
                        self._removed_sizes.append(size_bytes)
                        logger.debug(f"[Cleanup] 删除: {file_path}")
            except OSError as exc:
                err = f"[Cleanup] 删除失败 {file_path}: {exc}"
                logger.warning(err)
                self._errors.append(err)

    def get_active_tasks(self) -> List[str]:
        """
        从 manifest.json 读取当前活跃任务列表。
        活跃任务的文件不会被清理（即使超过 retention 时间）。
        """
        manifest_path = self.output_dir / "manifest.json"
        if not manifest_path.exists():
            return []

        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            return data.get("active_tasks", [])
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning(f"[Cleanup] 读取 manifest 失败: {exc}")
            return []

    def update_manifest(self, task_ids: List[str]) -> None:
        """
        将活跃任务 ID 列表写入 manifest.json。
        清理器会跳过 manifest 中记录的任务。
        """
        manifest_path = self.output_dir / "manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps(
                {
                    "active_tasks": task_ids,
                    "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        logger.debug(f"[Cleanup] manifest 已更新: {len(task_ids)} 个活跃任务")

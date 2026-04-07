"""
tests/test_task_manager.py — 任务清理工具测试
==============================================
"""

import json
import time
import tempfile
import os
from pathlib import Path

import pytest

from backend.utils.task_manager import TaskCleanup


class TestTaskCleanup:
    """TaskCleanup 功能测试"""

    @pytest.fixture
    def temp_dirs(self, tmp_path):
        """创建临时测试目录"""
        output_dir = tmp_path / "outputs"
        upload_dir = tmp_path / "uploads"
        output_dir.mkdir()
        upload_dir.mkdir()
        return output_dir, upload_dir

    def test_dry_run_does_not_delete(self, temp_dirs):
        """dry_run=True 时不删除任何文件"""
        output_dir, upload_dir = temp_dirs

        # 创建测试文件，mtime 设为 10 小时前
        old_file = output_dir / "test.gta.txt"
        old_file.write_text("old content")
        old_time = time.time() - 10 * 3600
        os.utime(old_file, (old_time, old_time))

        cleanup = TaskCleanup(
            output_dir=output_dir,
            upload_dir=upload_dir,
            retention_sec=3600,
            dry_run=True,
        )
        report = cleanup.run()

        assert old_file.exists(), "dry_run 模式不应删除文件"
        assert len(report["removed"]) == 0
        assert report["dry_run"] is True

    def test_removes_old_files(self, temp_dirs):
        """超过 retention_sec 的文件应被删除"""
        output_dir, upload_dir = temp_dirs

        old_file = output_dir / "old.pdf"
        old_file.write_text("old pdf content")
        old_time = time.time() - 2 * 3600
        os.utime(old_file, (old_time, old_time))

        new_file = output_dir / "new.gta.txt"
        new_file.write_text("new content")

        cleanup = TaskCleanup(
            output_dir=output_dir,
            upload_dir=upload_dir,
            retention_sec=3600,
            dry_run=False,
        )
        report = cleanup.run()

        assert not old_file.exists(), "旧文件应被删除"
        assert new_file.exists(), "新文件不应被删除"
        assert len(report["removed"]) == 1
        assert report["freed_mb"] >= 0

    def test_skips_manifest_file(self, temp_dirs):
        """manifest.json 不应被删除"""
        output_dir, upload_dir = temp_dirs

        manifest = output_dir / "manifest.json"
        manifest.write_text('{"active_tasks": []}')

        cleanup = TaskCleanup(
            output_dir=output_dir,
            upload_dir=upload_dir,
            retention_sec=0,
            dry_run=False,
        )
        cleanup.run()

        assert manifest.exists(), "manifest.json 不应被删除"

    def test_skips_nonexistent_directory(self, temp_dirs):
        """不存在的目录不应报错"""
        output_dir, upload_dir = temp_dirs

        cleanup = TaskCleanup(
            output_dir=output_dir / "nonexistent",
            upload_dir=upload_dir,
            retention_sec=3600,
            dry_run=False,
        )
        # 不应抛出异常
        report = cleanup.run()
        assert len(report["errors"]) == 0

    def test_update_and_get_manifest(self, temp_dirs):
        """manifest 读写功能"""
        output_dir, upload_dir = temp_dirs

        cleanup = TaskCleanup(
            output_dir=output_dir,
            upload_dir=upload_dir,
        )
        task_ids = ["task-001", "task-002", "task-003"]
        cleanup.update_manifest(task_ids)

        active = cleanup.get_active_tasks()
        assert active == task_ids

    def test_manifest_handles_corruption(self, temp_dirs):
        """manifest 损坏时 get_active_tasks 返回空列表"""
        output_dir, upload_dir = temp_dirs

        manifest = output_dir / "manifest.json"
        manifest.write_text("not valid json {{{")

        cleanup = TaskCleanup(
            output_dir=output_dir,
            upload_dir=upload_dir,
        )
        active = cleanup.get_active_tasks()
        assert active == []

    def test_upload_extension_filtering(self, temp_dirs):
        """上传目录只清理音频/视频文件"""
        output_dir, upload_dir = temp_dirs

        # 创建不同类型文件
        (upload_dir / "audio.mp3").write_text("mp3")
        (upload_dir / "audio.wav").write_text("wav")
        (upload_dir / "video.mp4").write_text("mp4")
        (upload_dir / "document.txt").write_text("text")  # 不应被清理
        (upload_dir / "script.py").write_text("python")  # 不应被清理

        old_time = time.time() - 7200
        for f in [upload_dir / "audio.mp3", upload_dir / "video.mp4"]:
            os.utime(f, (old_time, old_time))
        # txt 和 py 不改 mtime，保持新

        cleanup = TaskCleanup(
            output_dir=output_dir,
            upload_dir=upload_dir,
            retention_sec=3600,
            dry_run=False,
        )
        report = cleanup.run()

        assert (upload_dir / "audio.mp3").exists() is False
        assert (upload_dir / "video.mp4").exists() is False
        assert (upload_dir / "document.txt").exists() is True
        assert (upload_dir / "script.py").exists() is True

    def test_freed_mb_calculation(self, temp_dirs):
        """freed_mb 应正确计算释放空间"""
        output_dir, upload_dir = temp_dirs

        # 创建 100KB 文件，mtime 设为 2 小时前
        content = "x" * 102400
        f1 = output_dir / "big.gta.txt"
        f1.write_text(content)
        old_mtime = time.time() - 7200  # 2小时前
        os.utime(f1, (old_mtime, old_mtime))

        # 验证 mtime 设置正确
        actual_mtime = f1.stat().st_mtime
        assert actual_mtime < time.time() - 3600, f"mtime 未正确设置: {actual_mtime}"

        cleanup = TaskCleanup(
            output_dir=output_dir,
            upload_dir=upload_dir,
            retention_sec=3600,
            dry_run=False,
        )
        report = cleanup.run()

        assert len(report["removed"]) >= 1, f"应至少删除 1 个文件, got: {report['removed']}"
        assert report["freed_mb"] > 0, f"freed_mb 应 > 0, got {report['freed_mb']}"
        assert report["freed_mb"] < 1  # 约 0.1MB

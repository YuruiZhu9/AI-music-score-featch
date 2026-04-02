"""
测试：环境变量配置 — backend/core/config.py
============================================
验证 Settings 类所有字段、路径解析、验证器的行为。
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


class TestSettingsBasics:
    """基础配置项测试"""

    def test_defaults(self):
        from backend.core.config import Settings
        s = Settings()
        assert s.APP_NAME == "AI Guitar Tab Transcriber"
        assert s.APP_VERSION == "0.1.0"
        assert s.DEBUG is False

    def test_app_name_override(self):
        from backend.core.config import Settings
        s = Settings(APP_NAME="My App")
        assert s.APP_NAME == "My App"


class TestPathConfig:
    """路径配置测试"""

    def test_upload_dir_resolved(self):
        from backend.core.config import Settings
        with patch.dict(os.environ, {"UPLOAD_DIR": "/tmp/my_uploads"}):
            s = Settings()
            assert s.UPLOAD_DIR == Path("/tmp/my_uploads")

    def test_output_dir_resolved(self):
        from backend.core.config import Settings
        with patch.dict(os.environ, {"OUTPUT_DIR": "/tmp/my_outputs"}):
            s = Settings()
            assert s.OUTPUT_DIR == Path("/tmp/my_outputs")

    def test_model_cache_dir_resolved(self):
        from backend.core.config import Settings
        with patch.dict(os.environ, {"MODEL_CACHE_DIR": "/tmp/model_cache"}):
            s = Settings()
            assert s.MODEL_CACHE_DIR == Path("/tmp/model_cache")

    def test_relative_path_resolved(self):
        """相对路径应被解析为相对于项目根目录（backend/ 的上一级）"""
        from backend.core.config import Settings
        # UPLOAD_DIR=./uploads → 应在项目根目录下
        with patch.dict(os.environ, {"UPLOAD_DIR": "./test_uploads"}):
            s = Settings()
            # 解析为绝对路径
            assert s.UPLOAD_DIR.is_absolute()

    def test_dirs_created(self):
        """配置时自动创建目录"""
        import tempfile
        from backend.core.config import Settings
        with tempfile.TemporaryDirectory() as tmpdir:
            upload = Path(tmpdir) / "uploads"
            with patch.dict(os.environ, {"UPLOAD_DIR": str(upload)}):
                s = Settings()
                assert upload.exists()


class TestAudioConfig:
    """音频处理配置测试"""

    def test_sample_rate_default(self):
        from backend.core.config import Settings
        s = Settings()
        assert s.SAMPLE_RATE == 44100

    def test_bpm_defaults(self):
        from backend.core.config import Settings
        s = Settings()
        assert s.BPM_MIN == 40
        assert s.BPM_MAX == 220
        assert s.BPM_DEFAULT == 120

    def test_crepe_model_capacity(self):
        from backend.core.config import Settings
        s = Settings()
        assert s.CREPE_MODEL_CAPACITY == "full"
        assert s.CREPE_CONFIDENCE_THRESHOLD == 0.25

    def test_crepe_confidence_bounds(self):
        """置信度阈值必须在 0~1"""
        from backend.core.config import Settings
        s = Settings(CREPE_CONFIDENCE_THRESHOLD=0.5)
        assert s.CREPE_CONFIDENCE_THRESHOLD == 0.5


class TestDemucsConfig:
    """Demucs 音频分离配置测试"""

    def test_demucs_model_default(self):
        from backend.core.config import Settings
        s = Settings()
        assert s.DEMUCS_MODEL == "htdemucs"

    def test_demucs_device_default(self):
        from backend.core.config import Settings
        s = Settings()
        assert s.DEMUCS_DEVICE == "auto"


class TestFileLimitConfig:
    """文件限制配置测试"""

    def test_max_file_size_default(self):
        from backend.core.config import Settings
        s = Settings()
        assert s.MAX_FILE_SIZE_MB == 100

    def test_allowed_types(self):
        from backend.core.config import Settings
        s = Settings()
        assert "audio/mpeg" in s.ALLOWED_AUDIO_TYPES
        assert "audio/wav" in s.ALLOWED_AUDIO_TYPES
        assert "audio/flac" in s.ALLOWED_AUDIO_TYPES
        assert "video/mp4" in s.ALLOWED_AUDIO_TYPES

    def test_is_audio_allowed(self):
        from backend.core.config import Settings
        s = Settings()
        assert s.is_audio_allowed("audio/mpeg") is True
        assert s.is_audio_allowed("audio/wav") is True
        assert s.is_audio_allowed("text/plain") is False
        assert s.is_audio_allowed("image/png") is False


class TestScoreGenerationConfig:
    """乐谱生成配置测试"""

    def test_gta_beat_width_default(self):
        from backend.core.config import Settings
        s = Settings()
        assert s.GTA_BEAT_WIDTH == 4

    def test_max_tab_bars(self):
        from backend.core.config import Settings
        s = Settings()
        assert s.MAX_TAB_BARS == 64

    def test_pdf_engine_default(self):
        from backend.core.config import Settings
        s = Settings()
        assert s.PDF_ENGINE == "lilypond"


class TestPerformanceConfig:
    """性能配置测试"""

    def test_max_concurrent_tasks(self):
        from backend.core.config import Settings
        s = Settings()
        assert s.MAX_CONCURRENT_TASKS == 3
        # 范围 1-20
        s2 = Settings(MAX_CONCURRENT_TASKS=10)
        assert s2.MAX_CONCURRENT_TASKS == 10

    def test_task_timeout(self):
        from backend.core.config import Settings
        s = Settings()
        assert s.TASK_TIMEOUT_SEC == 600  # 10 分钟


class TestValidateBpm:
    """BPM 验证器测试"""

    def test_bpm_in_range(self):
        from backend.core.config import Settings
        s = Settings()
        assert s.validate_bpm(120) == 120

    def test_bpm_below_min(self):
        from backend.core.config import Settings
        s = Settings()
        # 小于下限 → 修正为下限
        assert s.validate_bpm(30) == s.BPM_MIN

    def test_bpm_above_max(self):
        from backend.core.config import Settings
        s = Settings()
        # 大于上限 → 修正为上限
        assert s.validate_bpm(300) == s.BPM_MAX

    def test_bpm_rounding(self):
        from backend.core.config import Settings
        s = Settings()
        # 浮点数 → 四舍五入取整
        assert s.validate_bpm(119.6) == 120
        assert s.validate_bpm(119.4) == 119


class TestCorsConfig:
    """CORS 配置测试"""

    def test_cors_origins_default(self):
        from backend.core.config import Settings
        s = Settings()
        assert s.CORS_ORIGINS == ["*"]

    def test_cors_origins_custom(self):
        """CORS 自定义配置：需要 JSON 格式"""
        from backend.core.config import Settings
        import json
        cors_json = json.dumps(["https://example.com", "https://app.com"])
        with patch.dict(os.environ, {"CORS_ORIGINS": cors_json}):
            s = Settings()
            assert "https://example.com" in s.CORS_ORIGINS
            assert "https://app.com" in s.CORS_ORIGINS


class TestGetSettings:
    """get_settings 单例测试"""

    def test_cached_singleton(self):
        from backend.core.config import get_settings
        s1 = get_settings()
        s2 = get_settings()
        # 同一对象（lru_cache 缓存）
        assert s1 is s2

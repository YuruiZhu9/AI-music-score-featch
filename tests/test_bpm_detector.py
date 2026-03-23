"""
测试：BPM 检测模块
===========================
使用 librosa 内置测试音频进行验证。
"""
import pytest
import numpy as np
from pathlib import Path

# Mock librosa 以便在无 GPU 环境下运行测试
try:
    import librosa
    HAS_LIBROSA = True
except ImportError:
    HAS_LIBROSA = False


@pytest.mark.skipif(not HAS_LIBROSA, reason="librosa 未安装")
class TestBPMDetector:
    """BPM 检测测试套件"""

    def test_bpm_basic(self, tmp_path):
        """生成1分钟正弦波音频，验证BPM检测"""
        import soundfile as sf

        sr = 22050
        duration = 30  # 秒
        bpm = 120
        freq = 440.0   # A4 正弦波

        # 生成正弦波
        t = np.linspace(0, duration, int(sr * duration), False)
        audio = np.sin(2 * np.pi * freq * t).astype(np.float32)

        # 保存临时音频
        audio_path = tmp_path / "test.wav"
        sf.write(str(audio_path), audio, sr)

        # 测试 BPM 检测
        from backend.core.bpm_detector import detect_bpm
        result = detect_bpm(audio_path, task_id="test")

        assert "bpm" in result
        assert result["bpm"] > 0
        print(f"✅ 检测到 BPM: {result['bpm']}")

    def test_bpm_returns_structure(self, tmp_path):
        """验证返回数据结构"""
        import soundfile as sf

        sr = 22050
        audio = np.random.randn(sr * 5).astype(np.float32) * 0.1
        audio_path = tmp_path / "noise.wav"
        sf.write(str(audio_path), audio, sr)

        from backend.core.bpm_detector import detect_bpm
        result = detect_bpm(audio_path, task_id="test_struct")

        assert "bpm" in result
        assert "time_signature" in result
        assert isinstance(result["bpm"], (int, float))
        assert isinstance(result["time_signature"], str)

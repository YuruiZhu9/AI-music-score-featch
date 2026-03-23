"""
测试：和弦识别模块
===========================
"""
import pytest
import numpy as np

try:
    import librosa
    HAS_LIBROSA = True
except ImportError:
    HAS_LIBROSA = False


@pytest.mark.skipif(not HAS_LIBROSA, reason="librosa 未安装")
class TestChordRecognizer:
    """和弦识别测试套件"""

    def test_returns_list(self, tmp_path):
        """验证返回格式为和弦列表"""
        import soundfile as sf

        sr = 22050
        # 生成 5 秒静音
        audio = np.zeros(sr * 5, dtype=np.float32)
        audio_path = tmp_path / "silence.wav"
        sf.write(str(audio_path), audio, sr)

        from backend.core.chord_recognizer import recognize_chords
        chords = recognize_chords(audio_path, task_id="test")

        assert isinstance(chords, list)
        print(f"✅ 和弦识别返回 {len(chords)} 个和弦")

    def test_chord_format(self, tmp_path):
        """验证每个和弦事件包含必需字段"""
        import soundfile as sf

        sr = 22050
        audio = np.random.randn(sr * 10).astype(np.float32) * 0.05
        audio_path = tmp_path / "random.wav"
        sf.write(str(audio_path), audio, sr)

        from backend.core.chord_recognizer import recognize_chords
        chords = recognize_chords(audio_path, task_id="test_format")

        for chord in chords:
            assert "start" in chord, "缺少 start 字段"
            assert "end" in chord, "缺少 end 字段"
            assert "chord" in chord, "缺少 chord 字段"
            assert chord["start"] < chord["end"], "start 必须小于 end"

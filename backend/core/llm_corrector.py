"""
LLM 智能纠错模块
=================
在 Pipeline 完成后，用大模型自动审查并修复扒谱结果中的常见错误：

1. 八度错音（Guitar 低音弦检测到高音区，疑似八度偏移）
2. 和弦类型错误（minor 写成 major，或遗漏 7/9 等扩展音）
3. 和弦进行逻辑错误（前一小节 Am 后突然 G# 极不自然）
4. 时值连续性错误（音符时值突然跳跃）
5. 根音推断（根据和弦上下文推断 Bass 根音）

调用方式：
    from backend.core.llm_corrector import correct_transcription
    corrected = correct_transcription(result_dict, api_key=None)  # 使用免费 API

"""

import os
import json
import logging
import textwrap
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# ─── 免费 LLM API ───────────────────────────────────────────────

def _call_zhipu(prompt: str, api_key: Optional[str] = None) -> str:
    """智谱 AI GLM-4-Flash（每日 200万Tokens免费）"""
    key = api_key or os.getenv("ZHIPU_API_KEY", "")
    if not key:
        raise RuntimeError("ZHIPU_API_KEY 未设置，请设置环境变量或在 .env 中配置。")

    import httpx
    with httpx.Client(timeout=60) as client:
        resp = client.post(
            "https://open.bigmodel.cn/api/paas/v4/chat/completions",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "glm-4-flash",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,  # 低温度保证纠错准确性
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


def _call_siliconflow(prompt: str, api_key: Optional[str] = None) -> str:
    """硅基流动（qwen-plus 每日2000次免费）"""
    key = api_key or os.getenv("SILICONFLOW_API_KEY", "")
    if not key:
        raise RuntimeError("SILICONFLOW_API_KEY 未设置。")

    import httpx
    with httpx.Client(timeout=60) as client:
        resp = client.post(
            "https://api.siliconflow.cn/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "Qwen/Qwen2.5-7B-Instruct",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


def _build_correction_prompt(
    chords: List[Dict[str, Any]],
    guitar_notes: List[Dict[str, Any]],
    bass_notes: List[Dict[str, Any]],
    bpm: int,
    time_signature: str,
    capo: int,
) -> str:
    """构造 LLM 纠错 prompt"""

    chords_str = json.dumps(chords, ensure_ascii=False, indent=2)
    guitar_str = json.dumps(guitar_notes[:50], ensure_ascii=False, indent=2)  # 限制数量
    bass_str = json.dumps(bass_notes[:50], ensure_ascii=False, indent=2)

    system_prompt = textwrap.dedent("""
        你是一位资深吉他手和音乐理论专家，擅长分析音乐和弦进行并纠正自动扒谱中的错误。
        你的任务是审查以下扒谱结果，找出问题并输出修正后的 JSON 数据。

        请严格按照以下规则纠错：

        1. 八度错误：如果 Guitar 音符明显在低音区（如 MIDI < 48）但和弦是 major，
           很可能检测低了一个八度，将该音符 pitch +12 修正。
           如果 Guitar 音符明显偏高（如 MIDI > 72），考虑 -12 修正。

        2. 和弦类型修正：
           - 常见错误：Em/E 混用、Gm/G 混用、Am/A 混用
           - 7和弦、maj7、minor7 等扩展和弦遗漏
           - 根据前后和弦进行推断（如 Am → D7 → G 是标准终止式，纠正不合理的离调和弦）

        3. 和弦进行逻辑：
           - 检测调性（如 C-Am-F-G 是 C 大调常见进行）
           - 标记不合理的和弦跳跃（如从 C 直接跳到 Bb 极不自然）
           - 修正建议：在备注中标注

        4. 时值连续性：
           - 如果相邻音符时值差异超过 4 倍，视为可疑（可能检测抖动）
           - Bass 音符时值通常较长（至少 1 拍），过短的可能是误检

        5. Capo 推断：
           - 如果检测到大量 #F、#G、#C 等高把位音符，且和弦简单，
             考虑 capo 夹在 2-5 品格，并据此修正转位

        输出格式（严格 JSON，无 markdown）：
        {
          "corrections": [
            {"type": "octave|chord|logic|timing|capo", "index": 0, "before": "...", "after": "...", "reason": "..."}
          ],
          "corrected_chords": [...],   // 修正后的和弦列表
          "corrected_guitar_notes": [...], // 修正后的吉他音符
          "corrected_bass_notes": [...],   // 修正后的贝斯音符
          "detected_key": "C",         // 推断调性
          "suggested_capo": 0,          // 推荐 capo 品位
          "summary": "纠错总结（10字内）"
        }

        如果没有问题，corrections 数组为空，直接原样返回原始数据。
    """).strip()

    user_prompt = f"""请审查以下扒谱结果：

曲速: {bpm} BPM
拍号: {time_signature}
Capo: {capo}

Guitar 和弦（{len(chords)} 个）:
{chords_str}

Guitar 音符（显示前 {min(50, len(guitar_notes))} 个）:
{guitar_str}

Bass 音符（显示前 {min(50, len(bass_notes))} 个）:
{bass_str}

请输出 JSON 纠错结果："""

    return f"{system_prompt}\n\n{user_prompt}"


def correct_transcription(
    result: Dict[str, Any],
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    对扒谱结果进行 LLM 智能纠错。

    参数:
        result: pipeline 输出的完整结果字典
        api_key: 可选手动传入 API key，否则读取环境变量

    返回:
        添加了 "llm_corrected" 字段的 result 字典：
        {
          ...result,
          "llm_corrected": {
            "corrected_chords": [...],
            "corrected_guitar_notes": [...],
            "corrected_bass_notes": [...],
            "corrections": [...],
            "detected_key": str,
            "suggested_capo": int,
            "summary": str,
          }
        }
    """
    chords = result.get("guitar", {}).get("chords", [])
    guitar_notes = result.get("guitar", {}).get("notes", [])
    bass_notes = result.get("bass", {}).get("notes", [])
    bpm = result.get("bpm", 120)
    time_sig = result.get("time_signature", "4/4")
    capo = result.get("capo", 0)

    if not chords and not guitar_notes:
        logger.warning("扒谱结果为空，跳过 LLM 纠错")
        result["llm_corrected"] = {"corrections": [], "summary": "无数据，跳过纠错"}
        return result

    prompt = _build_correction_prompt(chords, guitar_notes, bass_notes, bpm, time_sig, capo)

    # 优先使用智谱 AI
    errors = []
    try:
        raw = _call_zhipu(prompt, api_key)
        parsed = json.loads(raw)
        logger.info(f"LLM 纠错完成: {parsed.get('summary', 'OK')}")
    except Exception as e:
        errors.append(str(e))
        # fallback 硅基流动
        try:
            raw = _call_siliconflow(prompt, api_key)
            parsed = json.loads(raw)
            logger.info(f"LLM 纠错（硅基流动）完成: {parsed.get('summary', 'OK')}")
        except Exception as e2:
            errors.append(str(e2))
            logger.warning(f"LLM 纠错失败，跳过: {errors}")
            result["llm_corrected"] = {
                "corrections": [],
                "summary": f"纠错失败（API 不可用）",
                "error": "; ".join(errors),
            }
            return result

    # 合并纠错结果
    result["llm_corrected"] = {
        "corrected_chords": parsed.get("corrected_chords", chords),
        "corrected_guitar_notes": parsed.get("corrected_guitar_notes", guitar_notes),
        "corrected_bass_notes": parsed.get("corrected_bass_notes", bass_notes),
        "corrections": parsed.get("corrections", []),
        "detected_key": parsed.get("detected_key", "Unknown"),
        "suggested_capo": parsed.get("suggested_capo", 0),
        "summary": parsed.get("summary", ""),
    }

    # 如果 LLM 返回了修正数据，更新主数据
    if parsed.get("corrected_chords"):
        result["guitar"]["chords"] = parsed["corrected_chords"]
    if parsed.get("corrected_guitar_notes"):
        result["guitar"]["notes"] = parsed["corrected_guitar_notes"]
    if parsed.get("corrected_bass_notes"):
        result["bass"]["notes"] = parsed["corrected_bass_notes"]
    if parsed.get("detected_key"):
        result["detected_key"] = parsed["detected_key"]

    return result


# ─── Capo 自动检测 ──────────────────────────────────────────────

def detect_capo_and_key(
    chords: List[Dict[str, Any]],
    guitar_notes: List[Dict[str, Any]],
    bpm: int = 120,
) -> Dict[str, Any]:
    """
    根据检测到的和弦和音符，自动推断：
    1. 歌曲调性（如 C Major / A Minor）
    2. Capo 位置（还原品位）

    算法：
    - 统计所有和弦根音，建立调性打分表
    - 估算 capo：将检测到的和弦根音向上投射到标准把位，
      计算最小 capo 数使所有和弦都在 0-4 把位内

    返回 {"detected_key": str, "suggested_capo": int, "confidence": float}
    """
    if not chords:
        return {"detected_key": "Unknown", "suggested_capo": 0, "confidence": 0.0}

    NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

    # 收集所有根音
    roots: List[str] = []
    for c in chords:
        name = c.get("chord", "")
        root = name.lstrip("ABCDEFGabcdefg#b♯♭")
        roots.append(root or name)

    # 调性打分（C Ionian, D Dorian, E Phrygian...）
    scales = {
        "C":  ["C", "D", "E", "F", "G", "A", "B"],
        "G":  ["G", "A", "B", "C", "D", "E", "F#"],
        "D":  ["D", "E", "F#", "G", "A", "B", "C#"],
        "A":  ["A", "B", "C#", "D", "E", "F#", "G#"],
        "E":  ["E", "F#", "G#", "A", "B", "C#", "D#"],
        "F":  ["F", "G", "A", "Bb", "C", "D", "E"],
        "Bb": ["Bb", "C", "D", "Eb", "F", "G", "A"],
        "Am": ["A", "B", "C", "D", "E", "F", "G"],
        "Em": ["E", "F#", "G", "A", "B", "C", "D"],
        "Dm": ["D", "E", "F", "G", "A", "Bb", "C"],
    }

    best_key = "C"
    best_score = 0
    for key, scale in scales.items():
        score = sum(1 for r in roots if r in scale)
        if score > best_score:
            best_score = score
            best_key = key

    # Capo 推断：如果根音集中在高调（高把位常见音），建议 capo
    high_fret_notes = 0
    for n in guitar_notes:
        midi = n.get("pitch", 60)
        # E2=40, A2=45, D3=50, G3=55, B3=59, e4=64（标准调弦）
        # 如果音符在 72 以上（MIDI > D5），可能用了 capo
        if midi > 72:
            high_fret_notes += 1

    capo = 0
    if high_fret_notes > len(guitar_notes) * 0.3:
        # 30%以上音符在高把位，建议 capo
        capo = 2  # 保守估计
    elif high_fret_notes > len(guitar_notes) * 0.5:
        capo = 5

    confidence = min(1.0, best_score / max(1, len(chords)))

    return {
        "detected_key": best_key,
        "suggested_capo": capo,
        "confidence": round(confidence, 2),
    }

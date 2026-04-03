"""
Pydantic 数据模型 — 前后端 API 交互数据类型
============================================
定义所有请求/响应数据结构，确保类型安全和自动文档。
"""

from enum import Enum
from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, ConfigDict, Field


# ─── 枚举类型 ─────────────────────────────────────────────────────

class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"      # 等待处理
    PROCESSING = "processing"  # 处理中
    DONE = "done"            # 完成
    ERROR = "error"          # 失败


class ScoreFormat(str, Enum):
    """支持的导出格式"""
    PDF = "pdf"
    MIDI = "midi"
    GP = "gp"               # Guitar Pro
    JSON = "json"
    GTA = "gta"             # ASCII 文本谱


# ─── 任务相关模型 ─────────────────────────────────────────────────

class TaskCreate(BaseModel):
    """创建任务的请求体（POST /api/upload 的表单字段）"""
    filename: Optional[str] = None


class TaskRecord(BaseModel):
    """
    任务记录 — 包含任务的所有状态信息。
    对应内存中的 TaskRecord（backend/main.py）。
    """
    task_id: str = Field(..., description="唯一任务ID（UUID）")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="当前状态")
    progress: float = Field(default=0.0, ge=0.0, le=1.0, description="完成进度 0.0~1.0")
    stage: str = Field(default="等待上传", description="当前处理阶段描述")
    song_name: Optional[str] = Field(None, description="歌曲名称（可选，用户指定或从URL提取）")
    input_url: Optional[str] = Field(None, description="视频URL（如果有）")
    input_path: Optional[str] = Field(None, description="本地文件路径")
    result: Optional[Dict[str, Any]] = Field(None, description="分析结果")
    error: Optional[str] = Field(None, description="错误信息")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(ser_json_timedelta="iso8601")


class TaskStatusResponse(BaseModel):
    """GET /api/task/{task_id} 响应"""
    task_id: str
    status: TaskStatus
    progress: float = Field(..., ge=0.0, le=1.0)
    stage: str
    error: Optional[str] = None


# ─── 分析结果模型 ─────────────────────────────────────────────────

class ChordEvent(BaseModel):
    """单个和弦事件"""
    start: float = Field(..., ge=0, description="开始时间（秒）")
    end: float = Field(..., ge=0, description="结束时间（秒）")
    chord: str = Field(..., description="和弦名称，如 'Am', 'G7', 'Cmaj7'")


class NoteEvent(BaseModel):
    """单个音符事件"""
    time: float = Field(..., ge=0, description="音符开始时间（秒）")
    frequency: Optional[float] = Field(None, description="频率（Hz）")
    note: str = Field(..., description="音符名，如 'E4', 'A3'")
    string: Optional[int] = Field(None, ge=1, le=6, description="弦号（1=e弦, 6=E弦）")
    fret: Optional[int] = Field(None, ge=0, le=24, description="品位（0=空弦）")
    duration: Optional[str] = Field(None, description="时值：whole/half/quarter/eighth/sixteenth")
    confidence: float = Field(default=0.0, ge=0, le=1, description="检测置信度")


class BpmInfo(BaseModel):
    """节拍信息"""
    bpm: int = Field(..., ge=30, le=300, description="每分钟节拍数")
    time_signature: str = Field(default="4/4", description="拍号")
    beat_times: List[float] = Field(default_factory=list, description="每个节拍的时间点（秒）")
    duration_sec: float = Field(..., ge=0, description="音频总时长（秒）")


class PitchResult(BaseModel):
    """音高检测结果"""
    notes: List[NoteEvent] = Field(default_factory=list, description="音符序列")
    total_notes: int = Field(0, description="音符总数")
    duration_sec: float = Field(0, ge=0, description="音频时长")


class ScoreFiles(BaseModel):
    """生成的乐谱文件路径"""
    gta: Optional[str] = Field(None, description="GTA 文本谱路径")
    pdf: Optional[str] = Field(None, description="PDF 乐谱路径")
    mid: Optional[str] = Field(None, description="MIDI 文件路径")
    gp:  Optional[str] = Field(None, description="Guitar Pro 文件路径")
    json_data: Optional[str] = Field(None, alias="json", description="JSON 结果路径")

    model_config = ConfigDict(populate_by_name=True)


class GuitarTrackResult(BaseModel):
    """Guitar 轨道结果"""
    chords: List[ChordEvent] = Field(default_factory=list, description="和弦序列")
    notes:  List[NoteEvent] = Field(default_factory=list, description="音符序列")


class BassNoteEvent(BaseModel):
    """Bass 音符事件（支持更多字段）"""
    start: float    = Field(..., ge=0, description="开始时间（秒）")
    end:   float    = Field(..., ge=0, description="结束时间（秒）")
    note:  str      = Field(..., description="音符名，如 'E1', 'A1', 'D2'")
    midi:  int      = Field(..., description="MIDI note number")
    frequency: Optional[float] = Field(None, description="频率（Hz）")
    string: int     = Field(..., ge=1, le=4, description="弦号（1=G弦, 4=E弦）")
    fret:  int       = Field(..., ge=0, le=24, description="品位")
    chord_root: Optional[str] = Field(None, description="推断的和弦根音")
    confidence: float = Field(default=0.8, ge=0, le=1)


class BassTrackResult(BaseModel):
    """Bass 轨道结果"""
    notes:  List[BassNoteEvent] = Field(default_factory=list, description="Bass 音符序列")
    chords: List[ChordEvent]    = Field(default_factory=list, description="Bass 和弦（根音推断）")


class AnalysisResult(BaseModel):
    """
    完整分析结果 — GET /api/result/{task_id} 响应
    双轨结构：guitar + bass，同时保留旧版兼容字段。
    """
    task_id: str
    bpm: int = Field(..., description="BPM")
    time_signature: str = Field(default="4/4")
    duration_sec: float = Field(..., ge=0)

    # ── 双轨结构 ─────────────────────────────────────────
    guitar: Optional[GuitarTrackResult] = Field(
        None, description="Guitar 轨道（和弦 + 音符）")
    bass:   Optional[BassTrackResult]   = Field(
        None, description="Bass 轨道（音符 + 根音）")

    # ── 旧版兼容字段 ──────────────────────────────
    chords: List[ChordEvent] = Field(default_factory=list)
    notes:  List[NoteEvent]  = Field(default_factory=list)
    pitch:  Optional[PitchResult]   = Field(None)
    score_files: Optional[ScoreFiles] = Field(None)
    gta_text: Optional[str] = Field(None)


# ─── 响应包装器 ───────────────────────────────────────────────────

class ApiResponse(BaseModel):
    """通用 API 响应包装器"""
    success: bool = True
    message: str = "操作成功"
    data: Optional[Dict[str, Any]] = None


class UploadResponse(BaseModel):
    """POST /api/upload 响应"""
    task_id: str
    status: str = "pending"
    message: str
    poll_url: str


class ErrorResponse(BaseModel):
    """错误响应"""
    detail: str
    error_code: Optional[str] = None


# ─── 节拍分析模型（beat_analyzer.py）────────────────────────────────────

class BeatEventModel(BaseModel):
    """单个节拍事件（含强度和 downbeat 标记）"""
    time: float = Field(..., ge=0, description="时间（秒）")
    strength: float = Field(default=0.5, ge=0.0, le=1.0, description="节拍强度 0.0~1.0")
    is_downbeat: bool = Field(default=False, description="是否为小节首拍（强拍）")
    bar: int = Field(default=1, ge=1, description="小节编号（从1开始）")
    beat_in_bar: int = Field(default=1, ge=1, description="拍在小节内的位置（1-based）")


class BeatAnalysisResultModel(BaseModel):
    """节拍模式分析结果 — 由 beat_analyzer.py 返回"""
    bpm: float = Field(..., description="检测到的 BPM")
    time_signature: str = Field(default="4/4", description="时间签名")
    beat_events: List[BeatEventModel] = Field(
        default_factory=list,
        description="所有节拍事件列表",
    )
    downbeats: List[float] = Field(
        default_factory=list,
        description="Downbeat 时间点（秒）",
    )
    regularity_score: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="节拍稳定性评分（1.0=完全规律）",
    )
    tempo_drift: float = Field(
        default=0.0, ge=0.0,
        description="BPM 漂移（各段 BPM 的标准差）",
    )
    avg_strength: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="平均节拍强度",
    )
    num_bars: int = Field(default=0, ge=0, description="总小节数")
    duration_sec: float = Field(..., ge=0, description="音频时长（秒）")

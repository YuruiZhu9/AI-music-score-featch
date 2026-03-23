/**
 * GTAViewer.tsx — GTA文本谱渲染组件
 * ================================
 * 将和弦序列 + BPM 渲染为 ASCII 格式吉他六线谱
 */
import type { ChordEvent } from "../api/client";

interface GTAViewerProps {
  chords: ChordEvent[];
  bpm: number;
  songName?: string;
  artist?: string;
  capo?: number;
}

/**
 * 将和弦序列转换为 GTA 格式文本谱
 */
export function generateGTAText({
  chords,
  bpm,
  songName = "未知歌曲",
  artist = "未知艺术家",
  capo = 0,
}: GTAViewerProps): string {
  const BEATS_PER_MEASURE = 4;
  const BEAT_DURATION = 60 / bpm; // 秒/拍
  const CHARS_PER_BEAT = 4; // 每个拍子占4个字符

  const strings = ["e", "B", "G", "D", "A", "E"];

  // 估算总小节数
  const totalBeats = chords.length > 0
    ? Math.ceil((chords[chords.length - 1].end || 0) / BEAT_DURATION)
    : 16;
  const totalMeasures = Math.ceil(totalBeats / BEATS_PER_MEASURE);

  // 为每个和弦在小节中分配拍数
  const beatWidth = BEATS_PER_MEASURE * CHARS_PER_BEAT; // 每小节16字符

  let lines: string[] = [];

  // 头部信息
  lines.push(`Song: ${songName}`);
  if (artist) lines.push(`Artist: ${artist}`);
  lines.push(`Tempo: ${bpm} BPM`);
  if (capo > 0) lines.push(`Capo: ${capo}`);
  lines.push("");

  // 初始化6条弦的空白谱
  const stringLines: string[][] = strings.map(() =>
    Array(totalMeasures * (beatWidth + 1)).fill(" ")
  );

  // 在每条弦上标注品位
  // MVP阶段：假设所有和弦都是开放和弦（品位0）
  // 后续版本根据和弦类型推断品位
  const fretByString: Record<string, string> = {
    // 简单的开放和弦映射（占位）
    // e|--0-|  B|--1-|  G|--0-|  D|--2-|  A|--2-|  E|--0-|
  };

  // 简化版：每个和弦显示为当前弦的空弦或空拍
  let beatCursor = 0;

  for (const chord of chords) {
    const chordBeats = Math.max(1, Math.round((chord.end - chord.start) / BEAT_DURATION));
    const chordName = chord.chord || "N";

    // 解析和弦根音，推断品位
    const rootNote = chordName.replace(/m|7|9|11|13|dim|aug|sus|maj|add|del/g, "");
    const noteToFret: Record<string, number> = {
      "C": 0, "D": 2, "E": 0, "F": 1, "G": 0, "A": 0, "B": 2,
      "C#": 1, "D#": 3, "F#": 2, "G#": 1, "A#": 1,
    };
    const rootFret = noteToFret[rootNote] ?? 0;

    // 在对应弦上标注品位
    // 简化为：在所有弦上标注根音品位（实际吉他指法更复杂）
    const fretStr = rootFret === 0 ? "0" : String(rootFret);

    for (let beat = 0; beat < Math.min(chordBeats, BEATS_PER_MEASURE); beat++) {
      const pos = beatCursor + beat * CHARS_PER_BEAT;
      if (pos >= stringLines[0].length) break;

      // 在每条弦的对应位置写品位
      stringLines.forEach((line, sIdx) => {
        // 简化为只在第1拍写品位，后续拍子用连字符
        if (beat === 0) {
          const fretChar = fretStr.length === 1 ? fretStr : fretStr.slice(0, 2);
          line[pos] = "|"; // 小节分隔
          for (let c = 0; c < CHARS_PER_BEAT - 1; c++) {
            if (pos + 1 + c < line.length) {
              line[pos + 1 + c] = c === Math.floor(CHARS_PER_BEAT / 2) - 1
                ? fretChar[c % fretChar.length]
                : "-";
            }
          }
        }
      });
    }

    beatCursor += chordBeats * CHARS_PER_BEAT;
  }

  // 输出六线谱
  strings.forEach((s, idx) => {
    const measure = stringLines[idx]
      .map((c, i) => (i % (beatWidth + 1) === beatWidth && c === " ") ? "|" : c)
      .join("")
      .trimEnd();
    lines.push(`${s}|${measure}|`);
  });

  // 和弦行
  lines.push("");
  lines.push(`Chords: ${chords.map((c) => c.chord).join(" ")}`);

  return lines.join("\n");
}

export default function GTAViewer({ chords, bpm, songName, artist, capo }: GTAViewerProps) {
  const gtaText = generateGTAText({ chords, bpm, songName, artist, capo });

  const handleCopy = () => {
    navigator.clipboard.writeText(gtaText);
    alert("已复制到剪贴板！");
  };

  const handleDownload = () => {
    const blob = new Blob([gtaText], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${songName || "tab"}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div>
      <div className="flex gap-2 mb-4">
        <button
          onClick={handleCopy}
          className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700"
        >
          📋 复制文本谱
        </button>
        <button
          onClick={handleDownload}
          className="px-4 py-2 bg-gray-100 text-gray-700 text-sm rounded-lg hover:bg-gray-200"
        >
          ⬇ 下载 .txt
        </button>
      </div>

      <pre className="bg-gray-900 text-green-400 font-mono text-xs p-4 rounded-xl overflow-x-auto leading-relaxed">
        {gtaText}
      </pre>

      <p className="text-xs text-gray-400 mt-2">
        💡 这是 GTA（Guitar Tab ASCII）格式的吉他谱。
        数字表示品位（0=空弦），| 小节线，- 延音。
      </p>
    </div>
  );
}

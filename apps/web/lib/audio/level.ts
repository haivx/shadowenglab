// Bộ đo mức âm và phát hiện im lặng thuần (REC-01): (state, samples, dtMs) -> state.
// Không có đối tượng Web Audio ở đây; actor ghi âm (02-14) đưa buffer của
// `AnalyserNode.getFloatTimeDomainData` vào từng khung.
//
// Các hằng số dưới đây là GIÁ TRỊ KHỞI ĐIỂM (RESEARCH A1, Pattern 5a), cần chỉnh bằng micro thật
// ở bước UAT cuối phase. Chưa được đo trên phần cứng của Liam.

/** Thời gian đầu dùng để ước lượng nền ồn. */
export const NOISE_WINDOW_MS = 300;
/** Có tiếng khi mức dB vượt nền ồn thêm ngần này. */
export const SPEECH_MARGIN_DB = 10;
/** Im lặng liên tục sau khi đã có tiếng thì báo dừng sớm. */
export const SILENCE_MS = 1000;
/** Sàn dB (RMS bằng 0). */
export const MIN_DB = -100;
/** Mức dB ứng với vạch cao nhất. */
export const TOP_DB = -10;
export const BAR_COUNT = 10;

export interface LevelState {
  elapsedMs: number;
  /** Tổng dB nhân thời lượng khung, dùng để lấy trung bình trong NOISE_WINDOW_MS đầu. */
  noiseDbMs: number;
  noiseMs: number;
  /** null cho tới khi có khung đầu tiên. */
  noiseFloorDb: number | null;
  /** Khung hiện tại có tiếng. */
  speech: boolean;
  /** Đã từng có tiếng kể từ đầu lượt ghi. */
  speechStarted: boolean;
  silenceMs: number;
  /** true đúng ở khung mà im lặng đạt SILENCE_MS (không lặp lại ở các khung sau). */
  silenceDetected: boolean;
  /** 0..BAR_COUNT vạch sáng. */
  bars: number;
}

export function createLevelState(): LevelState {
  return {
    elapsedMs: 0,
    noiseDbMs: 0,
    noiseMs: 0,
    noiseFloorDb: null,
    speech: false,
    speechStarted: false,
    silenceMs: 0,
    silenceDetected: false,
    bars: 0,
  };
}

function rmsDb(samples: Float32Array): number {
  if (samples.length === 0) return MIN_DB;
  let sumSquares = 0;
  for (const sample of samples) sumSquares += sample * sample;
  const rms = Math.sqrt(sumSquares / samples.length);
  return rms > 0 ? Math.max(MIN_DB, 20 * Math.log10(rms)) : MIN_DB;
}

function barsFor(db: number, floorDb: number): number {
  const span = TOP_DB - floorDb;
  if (span <= 0) return 0;
  const ratio = Math.min(1, Math.max(0, (db - floorDb) / span));
  return Math.round(ratio * BAR_COUNT);
}

export function updateLevel(
  state: LevelState,
  samples: Float32Array,
  dtMs: number,
): LevelState {
  const db = rmsDb(samples);
  const elapsedMs = state.elapsedMs + dtMs;

  // Khung nằm trong cửa sổ đầu: chỉ học nền ồn, chưa phát hiện tiếng.
  if (state.elapsedMs < NOISE_WINDOW_MS) {
    const noiseDbMs = state.noiseDbMs + db * dtMs;
    const noiseMs = state.noiseMs + dtMs;
    return {
      ...state,
      elapsedMs,
      noiseDbMs,
      noiseMs,
      noiseFloorDb: noiseMs > 0 ? noiseDbMs / noiseMs : db,
      speech: false,
      silenceDetected: false,
      bars: 0,
    };
  }

  const floorDb = state.noiseFloorDb ?? db;
  const speech = db > floorDb + SPEECH_MARGIN_DB;
  const speechStarted = state.speechStarted || speech;

  // Chỉ đếm im lặng sau khi đã có tiếng; tiếng quay lại thì đếm lại từ 0.
  const silenceMs = speechStarted && !speech ? state.silenceMs + dtMs : 0;
  const silenceDetected =
    silenceMs >= SILENCE_MS && state.silenceMs < SILENCE_MS;

  return {
    ...state,
    elapsedMs,
    speech,
    speechStarted,
    silenceMs,
    silenceDetected,
    bars: barsFor(db, floorDb),
  };
}

// Gain thuần cho NGHE LẠI bản ghi của người học (PLY-07): (kênh âm) -> hệ số nhân.
// Đây KHÔNG phải ngưỡng chấm điểm: bản ghi gửi đi chấm giữ nguyên từng byte, gain chỉ áp lên
// đường phát ra loa. Không có đối tượng Web Audio ở đây, kiểm thử được trong node.
//
// Các hằng số dưới đây là GIÁ TRỊ KHỞI ĐIỂM, cần chỉnh bằng tai ở bước UAT.

/** Mức RMS mục tiêu khi nghe lại (dBFS), ~0.1 tuyến tính. */
export const TARGET_RMS_DBFS = -20;
/** Gain tối đa (+18 dB). */
export const MAX_PLAYBACK_GAIN = 8;
/** Đỉnh sau gain không vượt mức này (~ -1 dBFS) để không clip. */
export const PEAK_CEILING = 0.89;
/** RMS dưới mức này (-80 dBFS) coi là im lặng, không nâng gain. */
export const SILENCE_RMS = 1e-4;

export interface Level {
  peak: number;
  rms: number;
}

/** Đo đỉnh và RMS, bỏ qua mẫu không hữu hạn (NaN/Infinity). */
export function measureLevel(samples: Float32Array): Level {
  let peak = 0;
  let sumSquares = 0;
  let count = 0;
  for (const sample of samples) {
    if (!Number.isFinite(sample)) continue;
    const abs = Math.abs(sample);
    if (abs > peak) peak = abs;
    sumSquares += sample * sample;
    count += 1;
  }
  if (count === 0) return { peak: 0, rms: 0 };
  return { peak, rms: Math.sqrt(sumSquares / count) };
}

/**
 * Gain đưa bản ghi về mức to mục tiêu: luôn hữu hạn, trong [1, MAX_PLAYBACK_GAIN].
 * Không bao giờ hạ âm lượng; tôn trọng đỉnh (gain x peak <= PEAK_CEILING khi gain > 1).
 * Dùng giá trị lớn nhất giữa các kênh để một kênh câm không kéo gain về 1.
 */
export function playbackGain(channels: readonly Float32Array[]): number {
  let peak = 0;
  let rms = 0;
  for (const channel of channels) {
    const level = measureLevel(channel);
    if (level.peak > peak) peak = level.peak;
    if (level.rms > rms) rms = level.rms;
  }
  if (rms < SILENCE_RMS || peak <= 0) return 1;
  const byRms = 10 ** (TARGET_RMS_DBFS / 20) / rms;
  const byPeak = PEAK_CEILING / peak;
  const gain = Math.min(byRms, byPeak, MAX_PLAYBACK_GAIN);
  return Number.isFinite(gain) ? Math.max(1, gain) : 1;
}

import { describe, expect, it } from "vitest";
import {
  MAX_PLAYBACK_GAIN,
  PEAK_CEILING,
  SILENCE_RMS,
  TARGET_RMS_DBFS,
  measureLevel,
  playbackGain,
} from "./playbackGain";

const SAMPLE_RATE = 16_000;

/** Sóng sin biên độ `amplitude`: RMS = amplitude / sqrt(2). */
function sine(amplitude: number, ms = 1000): Float32Array {
  const length = Math.round((SAMPLE_RATE * ms) / 1000);
  const out = new Float32Array(length);
  for (let i = 0; i < length; i += 1) {
    out[i] = amplitude * Math.sin((2 * Math.PI * 440 * i) / SAMPLE_RATE);
  }
  return out;
}

describe("playbackGain", () => {
  it("tín hiệu nhỏ được nâng tới RMS mục tiêu", () => {
    const samples = sine(0.02);
    const gain = playbackGain([samples]);
    expect(gain).toBeGreaterThan(1);
    const rms = (0.02 / Math.sqrt(2)) * gain;
    expect(rms).toBeCloseTo(10 ** (TARGET_RMS_DBFS / 20), 2);
  });

  it("tín hiệu rất nhỏ bị chặn ở trần x8", () => {
    expect(playbackGain([sine(0.001)])).toBe(MAX_PLAYBACK_GAIN);
  });

  it("tín hiệu to gần 1 giữ nguyên gain 1 và không clip", () => {
    const gain = playbackGain([sine(0.99)]);
    expect(gain).toBe(1);
    expect(gain * 0.99).toBeLessThanOrEqual(1);
  });

  it("đỉnh nhọn giới hạn gain để không vượt PEAK_CEILING", () => {
    const spiky = sine(0.02);
    spiky[100] = 0.5;
    const gain = playbackGain([spiky]);
    expect(gain).toBeGreaterThan(1);
    expect(gain * 0.5).toBeLessThanOrEqual(PEAK_CEILING + 1e-9);
    expect(gain).toBeLessThan(playbackGain([sine(0.02)]));
  });

  it("im lặng, rỗng và nhiễu dưới SILENCE_RMS đều cho gain 1 hữu hạn", () => {
    const faint = new Float32Array(1000).fill(SILENCE_RMS / 2);
    const cases: Float32Array[][] = [
      [new Float32Array(1000)],
      [],
      [new Float32Array(0)],
      [faint],
    ];
    for (const channels of cases) {
      const gain = playbackGain(channels);
      expect(Number.isFinite(gain)).toBe(true);
      expect(gain).toBe(1);
    }
  });

  it("mẫu NaN/Infinity lẫn trong tín hiệu nhỏ vẫn cho số hữu hạn trong [1, trần]", () => {
    const dirty = sine(0.02);
    dirty[10] = Number.NaN;
    dirty[20] = Number.POSITIVE_INFINITY;
    dirty[30] = Number.NEGATIVE_INFINITY;
    const gain = playbackGain([dirty]);
    expect(Number.isFinite(gain)).toBe(true);
    expect(gain).toBeGreaterThanOrEqual(1);
    expect(gain).toBeLessThanOrEqual(MAX_PLAYBACK_GAIN);
  });

  it("nhiều kênh: kênh câm không kéo gain về 1", () => {
    const mono = playbackGain([sine(0.02)]);
    const stereo = playbackGain([sine(0.02), new Float32Array(SAMPLE_RATE)]);
    expect(stereo).toBe(mono);
  });

  it("quét biên độ: luôn hữu hạn, trong [1, trần] và gain x peak <= PEAK_CEILING khi gain > 1", () => {
    for (const amplitude of [1e-5, 1e-3, 0.01, 0.1, 0.5, 1]) {
      const gain = playbackGain([sine(amplitude)]);
      expect(Number.isFinite(gain)).toBe(true);
      expect(gain).toBeGreaterThanOrEqual(1);
      expect(gain).toBeLessThanOrEqual(MAX_PLAYBACK_GAIN);
      if (gain > 1) {
        expect(gain * amplitude).toBeLessThanOrEqual(PEAK_CEILING + 1e-9);
      }
    }
  });
});

describe("measureLevel", () => {
  it("mảng rỗng cho peak 0 và rms 0", () => {
    expect(measureLevel(new Float32Array(0))).toEqual({ peak: 0, rms: 0 });
  });

  it("sóng sin biên độ a có peak ~ a và rms ~ a / sqrt(2)", () => {
    const level = measureLevel(sine(0.3));
    expect(level.peak).toBeCloseTo(0.3, 3);
    expect(level.rms).toBeCloseTo(0.3 / Math.sqrt(2), 3);
  });
});

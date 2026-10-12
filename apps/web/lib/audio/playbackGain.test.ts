import { describe, expect, it } from "vitest";
import { TARGET_RMS_DBFS, playbackGain } from "./playbackGain";

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
});

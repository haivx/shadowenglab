import { describe, expect, it } from "vitest";
import { createLevelState, updateLevel, type LevelState } from "./level";

const SAMPLE_RATE = 16_000;

/** Sóng sin biên độ `amplitude`: RMS = amplitude / sqrt(2). */
function sine(amplitude: number, ms: number): Float32Array {
  const length = Math.round((SAMPLE_RATE * ms) / 1000);
  const out = new Float32Array(length);
  for (let i = 0; i < length; i += 1) {
    out[i] = amplitude * Math.sin((2 * Math.PI * 440 * i) / SAMPLE_RATE);
  }
  return out;
}

const NOISE_AMPLITUDE = 0.0014; // RMS ~ 0.001 = -60 dB
const SPEECH_AMPLITUDE = 0.1; // RMS ~ 0.0707 = -23 dB

/** Cấp `totalMs` mili giây theo từng khung `frameMs`. */
function feed(
  state: LevelState,
  amplitude: number,
  totalMs: number,
  frameMs = 20,
) {
  let current = state;
  const frames: LevelState[] = [];
  for (let elapsed = 0; elapsed < totalMs; elapsed += frameMs) {
    current = updateLevel(current, sine(amplitude, frameMs), frameMs);
    frames.push(current);
  }
  return { state: current, frames };
}

describe("updateLevel", () => {
  it("300 ms đầu của nhiễu thấp đặt nền ồn quanh -60 dB và chưa báo có tiếng", () => {
    const { state, frames } = feed(createLevelState(), NOISE_AMPLITUDE, 300);
    expect(state.noiseFloorDb).not.toBeNull();
    expect(state.noiseFloorDb ?? 0).toBeCloseTo(-60, 0);
    expect(frames.every((frame) => !frame.speech)).toBe(true);
    expect(state.speechStarted).toBe(false);
  });

  it("sóng sin 0.1 sau khi có nền ồn báo speech=true và sáng từ 5 vạch trở lên", () => {
    const calibrated = feed(createLevelState(), NOISE_AMPLITUDE, 300).state;
    const next = updateLevel(calibrated, sine(SPEECH_AMPLITUDE, 20), 20);
    expect(next.speech).toBe(true);
    expect(next.speechStarted).toBe(true);
    expect(next.bars).toBeGreaterThanOrEqual(5);
    expect(next.bars).toBeLessThanOrEqual(10);
  });

  it("nhiễu ở mức nền không bao giờ sáng vạch quá thấp (0 vạch)", () => {
    const { state } = feed(createLevelState(), NOISE_AMPLITUDE, 600);
    expect(state.bars).toBe(0);
    expect(state.speech).toBe(false);
  });

  it("sau khi có tiếng, 1000 ms khung mức nền báo im lặng đúng một lần, không sớm hơn", () => {
    let state = feed(createLevelState(), NOISE_AMPLITUDE, 300).state;
    state = feed(state, SPEECH_AMPLITUDE, 400).state;
    const quiet = feed(state, NOISE_AMPLITUDE, 1500, 100);
    const detectedAt = quiet.frames.flatMap((frame, i) =>
      frame.silenceDetected ? [i] : [],
    );
    expect(detectedAt).toEqual([9]); // khung thứ 10 = đủ 1000 ms
  });

  it("tiếng quay lại trước 1 s thì đếm im lặng về 0", () => {
    let state = feed(createLevelState(), NOISE_AMPLITUDE, 300).state;
    state = feed(state, SPEECH_AMPLITUDE, 200).state;
    state = feed(state, NOISE_AMPLITUDE, 800, 100).state;
    expect(state.silenceDetected).toBe(false);
    state = updateLevel(state, sine(SPEECH_AMPLITUDE, 100), 100);
    expect(state.silenceMs).toBe(0);
    const after = feed(state, NOISE_AMPLITUDE, 900, 100);
    expect(after.frames.some((frame) => frame.silenceDetected)).toBe(false);
  });

  it("im lặng trước khi có tiếng không bao giờ báo im lặng", () => {
    const { frames } = feed(createLevelState(), NOISE_AMPLITUDE, 5000, 100);
    expect(frames.some((frame) => frame.silenceDetected)).toBe(false);
    expect(frames.at(-1)?.speechStarted).toBe(false);
  });

  it("không đổi state đầu vào (hàm thuần)", () => {
    const initial = createLevelState();
    updateLevel(initial, sine(SPEECH_AMPLITUDE, 20), 20);
    expect(initial).toEqual(createLevelState());
  });

  it("khung rỗng (0 mẫu) được coi là im lặng tuyệt đối, không NaN", () => {
    const next = updateLevel(createLevelState(), new Float32Array(0), 20);
    expect(Number.isFinite(next.noiseFloorDb ?? 0)).toBe(true);
    expect(next.bars).toBe(0);
  });
});

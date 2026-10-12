import { describe, expect, it } from "vitest";
import { playbackGain } from "../audio/playbackGain";
import {
  playBlobOnce,
  type BlobPlaybackDeps,
  type DecodedLike,
  type PlaybackContextLike,
  type SourceLike,
} from "./listenActors";

const SAMPLE_RATE = 16_000;

/** Sóng sin biên độ `amplitude` dài 1 s. */
function sine(amplitude: number): Float32Array {
  const out = new Float32Array(SAMPLE_RATE);
  for (let i = 0; i < out.length; i += 1) {
    out[i] = amplitude * Math.sin((2 * Math.PI * 440 * i) / SAMPLE_RATE);
  }
  return out;
}

/** Chờ các microtask của chuỗi readBlob -> decode -> connect chạy xong. */
function flush(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, 0));
}

class FakeSource implements SourceLike {
  onended: (() => void) | null = null;
  stops = 0;
  starts = 0;
  constructor(private readonly startRejects: boolean) {}
  start() {
    this.starts += 1;
    return this.startRejects
      ? Promise.reject(new Error("blocked"))
      : Promise.resolve();
  }
  stop() {
    this.stops += 1;
  }
}

class FakeDecoded implements DecodedLike {
  gains: number[] = [];
  source: FakeSource | undefined;
  constructor(
    readonly channels: readonly Float32Array[],
    private readonly startRejects: boolean,
  ) {}
  connect(gain: number): SourceLike {
    this.gains.push(gain);
    this.source = new FakeSource(this.startRejects);
    return this.source;
  }
}

interface FakeOptions {
  channels?: readonly Float32Array[];
  startRejects?: boolean;
}

function fakeDeps(options: FakeOptions = {}) {
  const decoded = new FakeDecoded(
    options.channels ?? [sine(0.02)],
    options.startRejects ?? false,
  );
  const state = {
    closes: 0,
    createContexts: 0,
    readBlobs: [] as Blob[],
    decoded,
  };
  const context: PlaybackContextLike = {
    decode: () => Promise.resolve(decoded),
    close: () => {
      state.closes += 1;
    },
  };
  const deps: BlobPlaybackDeps = {
    readBlob: (blob) => {
      state.readBlobs.push(blob);
      return Promise.resolve(new ArrayBuffer(8));
    },
    createContext: () => {
      state.createContexts += 1;
      return context;
    },
  };
  return { deps, state };
}

describe("playBlobOnce", () => {
  it("resolve khi phát xong, connect nhận đúng gain chuẩn hoá và đóng context một lần", async () => {
    const { deps, state } = fakeDeps();
    const done = playBlobOnce(
      new Blob(["x"]),
      new AbortController().signal,
      deps,
    );
    await flush();
    state.decoded.source?.onended?.();
    await expect(done).resolves.toBeUndefined();
    expect(state.decoded.gains).toEqual([playbackGain(state.decoded.channels)]);
    expect(state.decoded.gains[0]).toBeGreaterThan(1);
    expect(state.closes).toBe(1);
  });

  it("huỷ giữa chừng thì stop đúng một lần, reject AbortError và đóng context một lần", async () => {
    const { deps, state } = fakeDeps();
    const controller = new AbortController();
    const done = playBlobOnce(new Blob(["x"]), controller.signal, deps);
    await flush();
    controller.abort();
    await expect(done).rejects.toMatchObject({ name: "AbortError" });
    expect(state.decoded.source?.stops).toBe(1);
    expect(state.closes).toBe(1);
  });

  it("signal đã huỷ từ trước thì không tạo context và không đọc Blob", async () => {
    const { deps, state } = fakeDeps();
    const controller = new AbortController();
    controller.abort();
    await expect(
      playBlobOnce(new Blob(["x"]), controller.signal, deps),
    ).rejects.toMatchObject({ name: "AbortError" });
    expect(state.createContexts).toBe(0);
    expect(state.readBlobs).toHaveLength(0);
  });

  it("start() bị từ chối thì reject đúng lỗi đó và vẫn đóng context", async () => {
    const { deps, state } = fakeDeps({ startRejects: true });
    await expect(
      playBlobOnce(new Blob(["x"]), new AbortController().signal, deps),
    ).rejects.toThrow("blocked");
    expect(state.closes).toBe(1);
  });
});

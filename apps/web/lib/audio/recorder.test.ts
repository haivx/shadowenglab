import { afterEach, describe, expect, it, vi } from "vitest";
import { createActor, setup } from "xstate";
import type { PlayerEvent } from "../player/playerMachine";
import {
  makeRecordActor,
  openMic,
  type MicHandle,
  type RecordDeps,
  type RecorderLike,
} from "./recorder";

/** rAF giả: test tự chạy từng khung. */
function fakeRaf() {
  let next = 1;
  const queue = new Map<number, (timeMs: number) => void>();
  return {
    raf: {
      request(callback: (timeMs: number) => void) {
        const id = next++;
        queue.set(id, callback);
        return id;
      },
      cancel(id: number) {
        queue.delete(id);
      },
    },
    get pending() {
      return queue.size;
    },
    step() {
      const frames = [...queue.entries()];
      queue.clear();
      for (const [, callback] of frames) callback(0);
    },
  };
}

class FakeRecorder implements RecorderLike {
  mimeType = "audio/webm;codecs=opus";
  state = "inactive";
  stopCalls = 0;
  private data: (blob: Blob) => void = () => undefined;
  private stopped: () => void = () => undefined;
  private failed: () => void = () => undefined;
  start() {
    this.state = "recording";
  }
  stop() {
    this.stopCalls += 1;
    this.state = "inactive";
    this.data(new Blob(["abc"], { type: this.mimeType }));
    this.stopped();
  }
  onData(callback: (blob: Blob) => void) {
    this.data = callback;
  }
  onStop(callback: () => void) {
    this.stopped = callback;
  }
  onError(callback: () => void) {
    this.failed = callback;
  }
  fail() {
    this.failed();
  }
}

function setupHarness(
  options: {
    level?: () => number;
    openMic?: RecordDeps["openMic"];
  } = {},
) {
  const frames = fakeRaf();
  let time = 0;
  const level = options.level ?? (() => 0);
  const recorder = new FakeRecorder();
  const closeMic = vi.fn();
  const createRecorder = vi.fn(() => recorder);
  const mic: MicHandle = {
    stream: {} as MediaStream,
    analyser: {
      fftSize: 64,
      getFloatTimeDomainData(array) {
        array.fill(level());
      },
    },
    close: closeMic,
  };
  const deps: Partial<RecordDeps> = {
    openMic: options.openMic ?? (async () => mic),
    createRecorder,
    isTypeSupported: (type) => type === "audio/webm;codecs=opus",
    readDeviceId: () => undefined,
    raf: frames.raf,
    now: () => time,
  };

  const events: PlayerEvent[] = [];
  const machine = setup({
    types: { events: {} as PlayerEvent | { type: "OFF" } },
    actors: { record: makeRecordActor(deps) },
  }).createMachine({
    id: "host",
    initial: "on",
    states: {
      on: {
        invoke: { id: "recorder", src: "record", input: { segmentIndex: 0 } },
        on: {
          "*": {
            actions: ({ event }) => {
              if (event.type !== "OFF") events.push(event);
            },
          },
          OFF: "off",
        },
      },
      off: {},
    },
  });
  const actor = createActor(machine);
  actor.start();

  return {
    actor,
    events,
    frames,
    recorder,
    closeMic,
    createRecorder,
    advance(ms: number) {
      time += ms;
      frames.step();
    },
    stop() {
      actor.getSnapshot().children.recorder?.send({ type: "STOP" });
    },
  };
}

const flush = () => new Promise((resolve) => setTimeout(resolve, 0));

describe("makeRecordActor", () => {
  it("STOP từ machine dừng recorder, gửi STOPPED với blob và trả micro", async () => {
    const h = setupHarness();
    await flush();
    expect(h.createRecorder).toHaveBeenCalled();
    h.advance(1500);
    h.stop();

    const stopped = h.events.find((event) => event.type === "STOPPED");
    expect(stopped).toBeDefined();
    if (stopped?.type !== "STOPPED") throw new Error("thiếu STOPPED");
    expect(stopped.blob.size).toBe(3);
    expect(stopped.blob.type).toBe("audio/webm;codecs=opus");
    expect(stopped.durationMs).toBe(1500);
    expect(h.closeMic).toHaveBeenCalled();
    expect(h.frames.pending).toBe(0);
    h.actor.stop();
  });

  it("không mở được micro thì gửi RECORD_FAILED", async () => {
    const h = setupHarness({
      openMic: async () => {
        throw new DOMException("denied", "NotAllowedError");
      },
    });
    await flush();
    expect(h.events).toContainEqual({ type: "RECORD_FAILED", reason: "mic" });
    expect(h.createRecorder).not.toHaveBeenCalled();
    h.actor.stop();
  });

  it("actor bị dọn trước khi micro mở xong thì micro được trả ngay và không ghi", async () => {
    const h = setupHarness();
    h.actor.send({ type: "OFF" });
    await flush();
    expect(h.closeMic).toHaveBeenCalled();
    expect(h.createRecorder).not.toHaveBeenCalled();
    expect(h.events).toHaveLength(0);
  });

  it("rời trạng thái khi đang ghi thì dừng recorder, huỷ rAF và đóng micro", async () => {
    const h = setupHarness();
    await flush();
    expect(h.frames.pending).toBe(1);
    h.actor.send({ type: "OFF" });
    expect(h.recorder.stopCalls).toBe(1);
    expect(h.closeMic).toHaveBeenCalled();
    expect(h.frames.pending).toBe(0);
    expect(h.events.some((event) => event.type === "STOPPED")).toBe(false);
  });

  it("gửi LEVEL khi mức đổi và SILENCE đúng một lần sau tiếng nói", async () => {
    let amplitude = 0.001;
    const h = setupHarness({ level: () => amplitude });
    await flush();

    // 300 ms đầu học nền ồn.
    for (let i = 0; i < 15; i += 1) h.advance(20);
    amplitude = 0.3;
    for (let i = 0; i < 10; i += 1) h.advance(20);
    expect(
      h.events.some((event) => event.type === "LEVEL" && event.speech),
    ).toBe(true);

    amplitude = 0.001;
    for (let i = 0; i < 70; i += 1) h.advance(20);
    expect(h.events.filter((event) => event.type === "SILENCE")).toHaveLength(
      1,
    );
    h.actor.stop();
  });

  it("MediaRecorder báo lỗi thì gửi RECORD_FAILED và trả micro", async () => {
    const h = setupHarness();
    await flush();
    h.recorder.fail();
    expect(h.events).toContainEqual({
      type: "RECORD_FAILED",
      reason: "recorder",
    });
    expect(h.closeMic).toHaveBeenCalled();
    h.actor.stop();
  });
});

describe("openMic", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("xin micro thô (không khử vọng/ồn/tự chỉnh gain, mono) và close() dừng track + đóng context", async () => {
    const trackStop = vi.fn();
    const getUserMedia = vi.fn(async () => ({
      getTracks: () => [{ stop: trackStop }, { stop: trackStop }],
    }));
    const contextClose = vi.fn(async () => undefined);
    class FakeAudioContext {
      state = "running";
      createAnalyser() {
        return { fftSize: 0, getFloatTimeDomainData: () => undefined };
      }
      createMediaStreamSource() {
        return { connect: () => undefined };
      }
      resume() {
        return Promise.resolve();
      }
      close() {
        this.state = "closed";
        return contextClose();
      }
    }
    vi.stubGlobal("navigator", { mediaDevices: { getUserMedia } });
    vi.stubGlobal("AudioContext", FakeAudioContext);

    const mic = await openMic("dev-1");
    expect(getUserMedia).toHaveBeenCalledWith({
      audio: {
        deviceId: { ideal: "dev-1" },
        echoCancellation: false,
        noiseSuppression: false,
        autoGainControl: false,
        channelCount: 1,
      },
    });
    expect(mic.analyser.fftSize).toBe(2048);

    mic.close();
    mic.close();
    expect(trackStop).toHaveBeenCalledTimes(2);
    expect(contextClose).toHaveBeenCalledTimes(1);
  });
});

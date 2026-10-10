// Test playRange / sampleWindow / makePlaySample (PLY-03): node env, video giả có currentTime
// tiến theo từng khung của rAF giả, không DOM thật.
import { describe, expect, it } from "vitest";
import { createActor, setup } from "xstate";
import {
  makePlaySample,
  playRange,
  sampleWindow,
  showSentenceFrame,
  type PlayableLesson,
  type RafLike,
  type VideoLike,
} from "./playRange";
import {
  playerMachine,
  type PlayerEvent,
  type PlayerInput,
  type PlaySampleInput,
} from "./playerMachine";

const FRAME_S = 0.02;

class FakeVideo implements VideoLike {
  private time = 0;
  playbackRate = 1;
  preservesPitch?: boolean;
  duration?: number;
  ended = false;
  playing = false;
  pauseCalls = 0;
  seeks: number[] = [];
  rejectPlayWith: Error | null = null;

  get currentTime(): number {
    return this.time;
  }
  set currentTime(value: number) {
    this.time = value;
    this.seeks.push(value);
  }

  play(): Promise<void> {
    if (this.rejectPlayWith) return Promise.reject(this.rejectPlayWith);
    this.playing = true;
    return Promise.resolve();
  }

  pause(): void {
    this.playing = false;
    this.pauseCalls += 1;
  }

  /** Thời gian trôi trong một khung hình (không ghi vào `seeks`). */
  advance(seconds: number): void {
    this.time += seconds;
  }
}

class FakeRaf implements RafLike {
  private nextId = 1;
  private callbacks = new Map<number, (timeMs: number) => void>();
  cancelled = 0;

  constructor(private readonly video: FakeVideo) {}

  request(callback: (timeMs: number) => void): number {
    const id = this.nextId;
    this.nextId += 1;
    this.callbacks.set(id, callback);
    return id;
  }

  cancel(id: number): void {
    if (this.callbacks.delete(id)) this.cancelled += 1;
  }

  get pending(): number {
    return this.callbacks.size;
  }

  /** Một khung hình: video phát tiến lên, sau đó chạy các callback đã hẹn. */
  tick(): void {
    if (this.video.playing) {
      this.video.advance(FRAME_S * this.video.playbackRate);
    }
    const due = [...this.callbacks.values()];
    this.callbacks.clear();
    for (const callback of due) callback(0);
  }
}

/** Nhường microtask để các `await` trong actor chạy giữa hai khung hình. */
const flush = () => new Promise<void>((resolve) => setImmediate(resolve));

async function tickUntil(
  raf: FakeRaf,
  done: () => boolean,
  maxFrames = 2000,
): Promise<void> {
  for (let i = 0; i < maxFrames && !done(); i += 1) {
    await flush();
    raf.tick();
  }
  await flush();
}

const LESSON: PlayableLesson = {
  segments: [
    { start: 10, end: 12, endExtraMs: 0 },
    { start: 0.05, end: 1, endExtraMs: 300 },
    { start: 59.9, end: 60, endExtraMs: 0 },
  ],
  padMs: 150,
  durationSec: 60,
};

describe("sampleWindow", () => {
  it("pads both ends by padMs", () => {
    const w = sampleWindow({ start: 10, end: 12, endExtraMs: 0 }, 150, 60);
    expect(w.startS).toBeCloseTo(9.85, 6);
    expect(w.endS).toBeCloseTo(12.15, 6);
  });

  it("adds endExtraMs after the end padding", () => {
    const w = sampleWindow({ start: 10, end: 12, endExtraMs: 300 }, 150, 60);
    expect(w.endS).toBeCloseTo(12.45, 6);
  });

  it("clamps the start at 0", () => {
    const w = sampleWindow({ start: 0.05, end: 1, endExtraMs: 0 }, 150, 60);
    expect(w.startS).toBe(0);
  });

  it("clamps the end at the video duration", () => {
    const w = sampleWindow({ start: 59.9, end: 60, endExtraMs: 300 }, 150, 60);
    expect(w.endS).toBe(60);
    expect(w.startS).toBeCloseTo(59.75, 6);
  });
});

describe("showSentenceFrame", () => {
  it("video đang dừng: tua tới đầu câu mới để khung hình đổi theo câu", () => {
    const video = { currentTime: 12.4, paused: true };

    expect(showSentenceFrame(video, 52.8)).toBe(true);
    expect(video.currentTime).toBe(52.8);
  });

  it("video đang phát (câu mẫu): không tua, để playRange tự quản lý", () => {
    const video = { currentTime: 12.4, paused: false };

    expect(showSentenceFrame(video, 52.8)).toBe(false);
    expect(video.currentTime).toBe(12.4);
  });

  it("đã ở đúng đầu câu thì không tua lại; mốc âm hoặc không hữu hạn bị bỏ qua", () => {
    const at = { currentTime: 52.8, paused: true };
    expect(showSentenceFrame(at, 52.8)).toBe(false);

    const bad = { currentTime: 3, paused: true };
    expect(showSentenceFrame(bad, Number.NaN)).toBe(false);
    expect(showSentenceFrame(bad, -1)).toBe(false);
    expect(bad.currentTime).toBe(3);
  });
});

describe("playRange", () => {
  it("stops at the end within one frame and pauses", async () => {
    const video = new FakeVideo();
    const raf = new FakeRaf(video);
    const controller = new AbortController();
    let settled = false;

    const promise = playRange(video, 1, 1.5, 1, controller.signal, raf).then(
      () => {
        settled = true;
      },
    );
    expect(video.seeks).toEqual([1]);

    await tickUntil(raf, () => settled);
    await promise;

    expect(video.currentTime).toBeGreaterThanOrEqual(1.5);
    expect(video.currentTime - 1.5).toBeLessThan(FRAME_S + 1e-9);
    expect(video.playing).toBe(false);
    expect(raf.pending).toBe(0);
  });

  it("sets the playback rate and keeps pitch", async () => {
    const video = new FakeVideo();
    const raf = new FakeRaf(video);
    let settled = false;
    const promise = playRange(
      video,
      0,
      0.1,
      0.75,
      new AbortController().signal,
      raf,
    ).then(() => {
      settled = true;
    });
    expect(video.playbackRate).toBe(0.75);
    expect(video.preservesPitch).toBe(true);
    await tickUntil(raf, () => settled);
    await promise;
  });

  it("aborts: cancels the frame loop, pauses and rejects with AbortError", async () => {
    const video = new FakeVideo();
    const raf = new FakeRaf(video);
    const controller = new AbortController();

    const promise = playRange(video, 1, 5, 1, controller.signal, raf);
    await flush();
    raf.tick();
    controller.abort();

    await expect(promise).rejects.toMatchObject({ name: "AbortError" });
    expect(video.playing).toBe(false);
    expect(raf.pending).toBe(0);
    expect(raf.cancelled).toBeGreaterThanOrEqual(1);
  });

  it("rejects immediately when the signal is already aborted", async () => {
    const video = new FakeVideo();
    const raf = new FakeRaf(video);
    const controller = new AbortController();
    controller.abort();
    await expect(
      playRange(video, 1, 2, 1, controller.signal, raf),
    ).rejects.toMatchObject({ name: "AbortError" });
    expect(video.seeks).toEqual([]);
  });

  it("rejects when play() is refused (autoplay policy)", async () => {
    const video = new FakeVideo();
    video.rejectPlayWith = new Error("NotAllowedError");
    const raf = new FakeRaf(video);
    await expect(
      playRange(video, 1, 2, 1, new AbortController().signal, raf),
    ).rejects.toThrow("NotAllowedError");
    expect(raf.pending).toBe(0);
  });

  it("stops when the video ends on its own before reaching the mark", async () => {
    const video = new FakeVideo();
    const raf = new FakeRaf(video);
    let settled = false;
    const promise = playRange(
      video,
      1,
      99,
      1,
      new AbortController().signal,
      raf,
    ).then(() => {
      settled = true;
    });
    await flush();
    raf.tick();
    video.ended = true;
    await tickUntil(raf, () => settled, 5);
    await promise;
    expect(video.playing).toBe(false);
  });
});

/** Cha giả ghi lại các sự kiện actor gửi ngược về. */
function runPlaySample(
  video: FakeVideo | null,
  raf: FakeRaf,
  input: PlaySampleInput,
) {
  const log: PlayerEvent[] = [];
  const logic = makePlaySample(
    () => video,
    () => LESSON,
    raf,
    {
      wait: () => Promise.resolve(),
    },
  );
  const parent = setup({
    types: { events: {} as PlayerEvent },
    actors: { child: logic },
  }).createMachine({
    initial: "run",
    states: {
      run: {
        invoke: { src: "child", input },
        on: {
          "*": {
            actions: ({ event }) => {
              log.push(event);
            },
          },
        },
      },
    },
  });
  const actor = createActor(parent).start();
  return { log, actor };
}

const doneOrFailed = (log: PlayerEvent[]) =>
  log.some((e) => e.type === "SAMPLE_DONE" || e.type === "SAMPLE_FAILED");

describe("makePlaySample", () => {
  it("repeat 2 sends REP 1, REP 2, then SAMPLE_DONE and seeks to the window start each pass", async () => {
    const video = new FakeVideo();
    const raf = new FakeRaf(video);
    const { log, actor } = runPlaySample(video, raf, {
      segmentIndex: 0,
      repeat: 2,
      rate: 1,
    });

    await tickUntil(raf, () => doneOrFailed(log));

    const relevant = log
      .filter((e) => ["REP", "SAMPLE_DONE", "SAMPLE_FAILED"].includes(e.type))
      .map((e) => (e.type === "REP" ? `REP ${e.n}` : e.type));
    expect(relevant).toEqual(["REP 1", "REP 2", "SAMPLE_DONE"]);
    expect(video.seeks).toHaveLength(2);
    expect(video.seeks[0]).toBeCloseTo(9.85, 6);
    expect(video.seeks[1]).toBeCloseTo(9.85, 6);
    expect(video.currentTime).toBeGreaterThanOrEqual(12.15);
    actor.stop();
  });

  it("clamps the window at the start and at the video duration", async () => {
    const video = new FakeVideo();
    video.duration = 60;
    const raf = new FakeRaf(video);
    const { log, actor } = runPlaySample(video, raf, {
      segmentIndex: 1,
      repeat: 1,
      rate: 1,
    });
    await tickUntil(raf, () => doneOrFailed(log));
    expect(video.seeks[0]).toBe(0);
    expect(log.some((e) => e.type === "SAMPLE_DONE")).toBe(true);
    actor.stop();

    const tail = new FakeVideo();
    tail.duration = 60;
    const tailRaf = new FakeRaf(tail);
    const tailRun = runPlaySample(tail, tailRaf, {
      segmentIndex: 2,
      repeat: 1,
      rate: 1,
    });
    await tickUntil(tailRaf, () => doneOrFailed(tailRun.log));
    expect(tail.currentTime).toBeGreaterThanOrEqual(60);
    expect(tail.currentTime).toBeLessThan(60 + FRAME_S + 1e-9);
    tailRun.actor.stop();
  });

  it("sends SAMPLE_FAILED when play() is refused", async () => {
    const video = new FakeVideo();
    video.rejectPlayWith = new Error("NotAllowedError");
    const raf = new FakeRaf(video);
    const { log, actor } = runPlaySample(video, raf, {
      segmentIndex: 0,
      repeat: 1,
      rate: 1,
    });
    await tickUntil(raf, () => doneOrFailed(log), 3);
    expect(log.some((e) => e.type === "SAMPLE_FAILED")).toBe(true);
    actor.stop();
  });

  it("sends SAMPLE_FAILED when there is no video element", async () => {
    const raf = new FakeRaf(new FakeVideo());
    const { log, actor } = runPlaySample(null, raf, {
      segmentIndex: 0,
      repeat: 1,
      rate: 1,
    });
    await flush();
    expect(log.some((e) => e.type === "SAMPLE_FAILED")).toBe(true);
    actor.stop();
  });

  it("cleans up on stop: pauses the video and sends nothing afterwards", async () => {
    const video = new FakeVideo();
    const raf = new FakeRaf(video);
    const { log, actor } = runPlaySample(video, raf, {
      segmentIndex: 0,
      repeat: 3,
      rate: 1,
    });
    await flush();
    raf.tick();
    actor.stop();
    await tickUntil(raf, () => false, 5);

    expect(video.playing).toBe(false);
    expect(raf.pending).toBe(0);
    expect(log.some((e) => e.type === "SAMPLE_DONE")).toBe(false);
    expect(log.some((e) => e.type === "SAMPLE_FAILED")).toBe(false);
  });
});

describe("playerMachine with the real playSample actor (tracer)", () => {
  const INPUT: PlayerInput = {
    segmentCount: 3,
    startIndex: 0,
    segmentDurationsMs: [2000, 950, 100],
    repeat: 2,
    rate: 0.75,
    recordFactor: 1.5,
  };

  function start(video: FakeVideo, raf: FakeRaf) {
    const machine = playerMachine.provide({
      actors: {
        playSample: makePlaySample(
          () => video,
          () => LESSON,
          raf,
          {
            wait: () => Promise.resolve(),
          },
        ),
      },
    });
    return createActor(machine, { input: INPUT }).start();
  }

  it("PLAY plays the padded sentence x repeat at the session rate, then moves to recording", async () => {
    const video = new FakeVideo();
    const raf = new FakeRaf(video);
    const actor = start(video, raf);

    actor.send({ type: "PLAY" });
    expect(actor.getSnapshot().value).toBe("playing");

    await flush();
    expect(actor.getSnapshot().context.rep).toBe(1);

    await tickUntil(raf, () => actor.getSnapshot().matches("recording"));

    expect(actor.getSnapshot().matches("recording")).toBe(true);
    expect(video.playbackRate).toBe(0.75);
    expect(video.seeks).toHaveLength(2);
    expect(video.seeks[0]).toBeCloseTo(9.85, 6);
    expect(actor.getSnapshot().context.rep).toBe(2);
    actor.stop();
  });

  it("STOP while playing returns to idle and pauses the video", async () => {
    const video = new FakeVideo();
    const raf = new FakeRaf(video);
    const actor = start(video, raf);

    actor.send({ type: "PLAY" });
    await flush();
    raf.tick();
    actor.send({ type: "STOP" });

    expect(actor.getSnapshot().value).toBe("idle");
    await tickUntil(raf, () => false, 5);
    expect(video.playing).toBe(false);
    expect(actor.getSnapshot().value).toBe("idle");
    actor.stop();
  });

  it("GOTO while playing stops playback and selects the sentence", async () => {
    const video = new FakeVideo();
    const raf = new FakeRaf(video);
    const actor = start(video, raf);

    actor.send({ type: "PLAY" });
    await flush();
    actor.send({ type: "GOTO", index: 2 });

    expect(actor.getSnapshot().value).toBe("idle");
    expect(actor.getSnapshot().context.segmentIndex).toBe(2);
    expect(video.playing).toBe(false);
    actor.stop();
  });
});

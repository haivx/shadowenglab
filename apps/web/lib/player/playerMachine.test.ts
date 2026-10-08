// Test các transition chính của playerMachine (PLY-02): node env, không DOM, actor giả.
import { afterEach, describe, expect, it, vi } from "vitest";
import { createActor, fromCallback, fromPromise, waitFor } from "xstate";
import type { AttemptAck } from "@shadowenglab/contracts";
import {
  playerMachine,
  type PlayBlobInput,
  type PlayBothInput,
  type PlayerEvent,
  type PlayerInput,
  type PlaySampleInput,
  type RecordInput,
  type UploadInput,
} from "./playerMachine";

const INPUT: PlayerInput = {
  segmentCount: 5,
  startIndex: 0,
  segmentDurationsMs: [2000, 3000, 2500, 2000, 4000],
  repeat: 1,
  rate: 1,
  recordFactor: 1.5,
};

type SendBack = (event: PlayerEvent) => void;

function ack(
  segmentIndex: number,
  attempt: number,
  voiced: boolean,
): AttemptAck {
  return {
    lessonId: "lesson-1",
    segmentIndex,
    attempt,
    durationMs: 1800,
    voiced,
    savedForEval: false,
  };
}

/** Bộ actor giả + tay cầm để test điều khiển từng bước. */
function makeFakes() {
  const calls = {
    samples: [] as PlaySampleInput[],
    sampleCleanups: 0,
    records: [] as RecordInput[],
    recorderStops: 0,
    uploads: [] as UploadInput[],
    blobs: [] as PlayBlobInput[],
    boths: [] as PlayBothInput[],
  };
  const ctl: {
    sample: SendBack | null;
    recorder: SendBack | null;
    upload: (input: UploadInput) => Promise<AttemptAck>;
  } = {
    sample: null,
    recorder: null,
    upload: async (input) => ack(input.segmentIndex, 1, true),
  };
  const actors = {
    playSample: fromCallback<PlayerEvent, PlaySampleInput>(
      ({ input, sendBack }) => {
        calls.samples.push(input);
        ctl.sample = sendBack;
        return () => {
          calls.sampleCleanups += 1;
        };
      },
    ),
    record: fromCallback<PlayerEvent, RecordInput>(
      ({ input, sendBack, receive }) => {
        calls.records.push(input);
        ctl.recorder = sendBack;
        receive((event) => {
          if (event.type === "STOP") calls.recorderStops += 1;
        });
        return () => {};
      },
    ),
    uploadAttempt: fromPromise<AttemptAck, UploadInput>(async ({ input }) => {
      calls.uploads.push(input);
      return ctl.upload(input);
    }),
    playBlob: fromPromise<undefined, PlayBlobInput>(async ({ input }) => {
      calls.blobs.push(input);
      await new Promise<never>(() => {});
    }),
    playBoth: fromPromise<undefined, PlayBothInput>(async ({ input }) => {
      calls.boths.push(input);
      await new Promise<never>(() => {});
    }),
  };
  return { calls, ctl, actors };
}

function start(overrides: Partial<PlayerInput> = {}) {
  const fakes = makeFakes();
  const actor = createActor(playerMachine.provide({ actors: fakes.actors }), {
    input: { ...INPUT, ...overrides },
  });
  actor.start();
  return { actor, ...fakes };
}

const BLOB = () => new Blob(["audio"], { type: "audio/webm" });

type Harness = ReturnType<typeof start>;

/** idle -> playing -> recording */
function toRecording(h: Harness) {
  h.actor.send({ type: "PLAY" });
  h.ctl.sample?.({ type: "SAMPLE_DONE" });
}

/** ... -> scoring (đã có blob) */
function toScoring(h: Harness, blob: Blob = BLOB()) {
  toRecording(h);
  h.ctl.recorder?.({ type: "STOPPED", blob, durationMs: 1800 });
  return blob;
}

async function toReviewing(h: Harness) {
  toScoring(h);
  await waitFor(h.actor, (s) => s.matches("reviewing"));
}

afterEach(() => {
  vi.useRealTimers();
});

describe("playerMachine: luồng chính", () => {
  it("idle -> playing -> recording -> scoring -> reviewing, lưu bản ghi đã tải lên", async () => {
    const h = start();
    expect(h.actor.getSnapshot().matches("idle")).toBe(true);

    h.actor.send({ type: "PLAY" });
    expect(h.actor.getSnapshot().matches("playing")).toBe(true);
    expect(h.calls.samples[0]).toEqual({ segmentIndex: 0, repeat: 1, rate: 1 });

    h.ctl.sample?.({ type: "SAMPLE_DONE" });
    expect(h.actor.getSnapshot().matches("recording")).toBe(true);
    expect(h.calls.records).toEqual([{ segmentIndex: 0 }]);

    const blob = BLOB();
    h.ctl.recorder?.({ type: "STOPPED", blob, durationMs: 1800 });
    expect(h.actor.getSnapshot().matches("scoring")).toBe(true);

    await waitFor(h.actor, (s) => s.matches("reviewing"));
    const snap = h.actor.getSnapshot();
    expect(snap.matches({ reviewing: "idle" })).toBe(true);
    expect(snap.context.recordings[0]?.status).toBe("uploaded");
    expect(snap.context.recordings[0]?.attempt).toBe(1);
    expect(snap.context.recordings[0]?.blob).toBe(blob);
    expect(h.calls.uploads[0]).toEqual({ segmentIndex: 0, blob });
  });

  it("Space (STOP) khi đang ghi gửi STOP cho recorder; STOPPED của recorder mới sang scoring", () => {
    const h = start();
    toRecording(h);
    h.actor.send({ type: "STOP" });
    expect(h.calls.recorderStops).toBe(1);
    expect(h.actor.getSnapshot().matches("recording")).toBe(true);

    h.ctl.recorder?.({ type: "STOPPED", blob: BLOB(), durationMs: 900 });
    expect(h.actor.getSnapshot().matches("scoring")).toBe(true);
  });

  it("tự dừng ghi sau độ dài câu x recordFactor tính từ RECORDING_STARTED; SILENCE cũng dừng", () => {
    vi.useFakeTimers();
    const h = start(); // câu 0 = 2000 ms, recordFactor 1.5 => 3000 ms
    toRecording(h);
    h.ctl.recorder?.({ type: "RECORDING_STARTED" });
    vi.advanceTimersByTime(2999);
    expect(h.calls.recorderStops).toBe(0);
    vi.advanceTimersByTime(1);
    expect(h.calls.recorderStops).toBe(1);

    const h2 = start();
    toRecording(h2);
    h2.actor.send({ type: "SILENCE" });
    expect(h2.calls.recorderStops).toBe(1);
  });

  it("chưa có RECORDING_STARTED (đang chờ cấp quyền micro) thì không tự dừng ghi", () => {
    vi.useFakeTimers();
    const h = start();
    toRecording(h);
    expect(h.actor.getSnapshot().matches({ recording: "opening" })).toBe(true);

    vi.advanceTimersByTime(10_000); // lâu hơn recordDelay 3000 ms
    expect(h.calls.recorderStops).toBe(0);
    expect(h.actor.getSnapshot().matches("recording")).toBe(true);

    h.ctl.recorder?.({ type: "RECORDING_STARTED" });
    expect(h.actor.getSnapshot().matches({ recording: "active" })).toBe(true);
    vi.advanceTimersByTime(3000);
    expect(h.calls.recorderStops).toBe(1);
  });

  it("uploadAttempt trả voiced=false -> noVoice; RECORD từ noVoice -> recording", async () => {
    const h = start();
    h.ctl.upload = async (input) => ack(input.segmentIndex, 1, false);
    toScoring(h);
    await waitFor(h.actor, (s) => s.matches("noVoice"));
    expect(h.actor.getSnapshot().context.recordings[0]?.status).toBe("noVoice");

    h.actor.send({ type: "RECORD" });
    expect(h.actor.getSnapshot().matches("recording")).toBe(true);
    expect(h.calls.records).toHaveLength(2);
  });

  it("uploadAttempt reject -> error, giữ nguyên blob, lastError; RETRY_UPLOAD gửi lại đúng blob; RECORD -> recording", async () => {
    const h = start();
    h.ctl.upload = async () => {
      throw new Error("backend 500");
    };
    const blob = toScoring(h);
    await waitFor(h.actor, (s) => s.matches("error"));
    let snap = h.actor.getSnapshot();
    expect(snap.context.recordings[0]?.blob).toBe(blob);
    expect(snap.context.recordings[0]?.status).toBe("failed");
    expect(snap.context.lastError).toBe("backend 500");

    h.ctl.upload = async (input) => ack(input.segmentIndex, 1, true);
    h.actor.send({ type: "RETRY_UPLOAD" });
    expect(h.actor.getSnapshot().matches("scoring")).toBe(true);
    expect(h.calls.uploads[1]?.blob).toBe(blob);
    await waitFor(h.actor, (s) => s.matches("reviewing"));

    // nhánh error -> RECORD
    const h2 = start();
    h2.ctl.upload = async () => {
      throw new Error("x");
    };
    toScoring(h2);
    await waitFor(h2.actor, (s) => s.matches("error"));
    h2.actor.send({ type: "RECORD" });
    snap = h2.actor.getSnapshot();
    expect(snap.matches("recording")).toBe(true);
  });

  it("RECORD_FAILED (mở micro lỗi) -> error với lastError 'mic'", () => {
    const h = start();
    toRecording(h);
    h.ctl.recorder?.({ type: "RECORD_FAILED", reason: "denied" });
    const snap = h.actor.getSnapshot();
    expect(snap.matches("error")).toBe(true);
    expect(snap.context.lastError).toBe("mic");
  });

  it("R (RECORD) từ reviewing -> recording; PLAY từ reviewing -> playing (lượt mới)", async () => {
    const h = start();
    await toReviewing(h);
    h.actor.send({ type: "RECORD" });
    expect(h.actor.getSnapshot().matches("recording")).toBe(true);

    const h2 = start();
    await toReviewing(h2);
    h2.actor.send({ type: "PLAY" });
    expect(h2.actor.getSnapshot().matches("playing")).toBe(true);
  });
});

describe("playerMachine: điều hướng và đồng thời", () => {
  it("NEXT/PREV/GOTO và PLAY bị bỏ qua khi đang ghi hoặc đang xử lý", () => {
    const h = start();
    toRecording(h);
    for (const event of [
      { type: "NEXT" },
      { type: "PREV" },
      { type: "GOTO", index: 3 },
      { type: "PLAY" },
      { type: "RECORD" },
      { type: "PREVIEW" },
    ] as const) {
      h.actor.send(event);
    }
    let snap = h.actor.getSnapshot();
    expect(snap.matches("recording")).toBe(true);
    expect(snap.context.segmentIndex).toBe(0);
    expect(h.calls.records).toHaveLength(1); // không bắt đầu lượt ghi thứ hai

    h.ctl.recorder?.({ type: "STOPPED", blob: BLOB(), durationMs: 1000 });
    h.ctl.upload = () => new Promise<AttemptAck>(() => {});
    for (const event of [
      { type: "NEXT" },
      { type: "GOTO", index: 2 },
      { type: "PLAY" },
    ] as const) {
      h.actor.send(event);
    }
    snap = h.actor.getSnapshot();
    expect(snap.matches("scoring")).toBe(true);
    expect(snap.context.segmentIndex).toBe(0);
  });

  it("NEXT ở câu cuối và PREV ở câu đầu không làm gì; GOTO(3) từ reviewing -> idle ở câu 3", async () => {
    const last = start({ startIndex: 4 });
    last.actor.send({ type: "NEXT" });
    expect(last.actor.getSnapshot().context.segmentIndex).toBe(4);

    const first = start();
    first.actor.send({ type: "PREV" });
    expect(first.actor.getSnapshot().context.segmentIndex).toBe(0);
    first.actor.send({ type: "GOTO", index: 9 });
    first.actor.send({ type: "GOTO", index: -1 });
    expect(first.actor.getSnapshot().context.segmentIndex).toBe(0);

    const h = start();
    await toReviewing(h);
    h.actor.send({ type: "GOTO", index: 3 });
    const snap = h.actor.getSnapshot();
    expect(snap.matches("idle")).toBe(true);
    expect(snap.context.segmentIndex).toBe(3);
  });

  it("PREVIEW (O) từ idle -> previewing (lặp 1) -> idle khi xong; STOP trong playing -> idle và dọn actor", () => {
    const h = start({ repeat: 3 });
    h.actor.send({ type: "PREVIEW" });
    expect(h.actor.getSnapshot().matches("previewing")).toBe(true);
    expect(h.calls.samples[0]).toEqual({ segmentIndex: 0, repeat: 1, rate: 1 });
    h.ctl.sample?.({ type: "SAMPLE_DONE" });
    expect(h.actor.getSnapshot().matches("idle")).toBe(true);
    expect(h.calls.sampleCleanups).toBe(1);

    h.actor.send({ type: "PLAY" });
    expect(h.calls.samples[1]).toEqual({ segmentIndex: 0, repeat: 3, rate: 1 });
    h.actor.send({ type: "STOP" });
    expect(h.actor.getSnapshot().matches("idle")).toBe(true);
    expect(h.calls.sampleCleanups).toBe(2);
  });

  it("rời playing bằng NEXT cũng dừng phát (cleanup) và sang câu mới", () => {
    const h = start();
    h.actor.send({ type: "PLAY" });
    h.actor.send({ type: "NEXT" });
    const snap = h.actor.getSnapshot();
    expect(snap.matches("idle")).toBe(true);
    expect(snap.context.segmentIndex).toBe(1);
    expect(h.calls.sampleCleanups).toBe(1);
  });

  it("sau previewing, quay về trạng thái theo bản ghi của câu (reviewing nếu đã tải lên)", async () => {
    const h = start();
    await toReviewing(h);
    h.actor.send({ type: "GOTO", index: 0 });
    expect(h.actor.getSnapshot().matches("idle")).toBe(true);
    h.actor.send({ type: "PREVIEW" });
    h.ctl.sample?.({ type: "SAMPLE_DONE" });
    expect(h.actor.getSnapshot().matches("reviewing")).toBe(true);
  });
});

describe("playerMachine: nghe lại và cài đặt", () => {
  it("reviewing: LISTEN_ORIGINAL -> original -> idle khi xong; LISTEN_YOURS -> yours; LISTEN_BOTH -> both", async () => {
    const h = start({ repeat: 2 });
    await toReviewing(h);

    h.actor.send({ type: "LISTEN_ORIGINAL" });
    expect(h.actor.getSnapshot().matches({ reviewing: "original" })).toBe(true);
    expect(h.calls.samples.at(-1)).toEqual({
      segmentIndex: 0,
      repeat: 1,
      rate: 1,
    });
    h.ctl.sample?.({ type: "SAMPLE_DONE" });
    expect(h.actor.getSnapshot().matches({ reviewing: "idle" })).toBe(true);

    h.actor.send({ type: "LISTEN_YOURS" });
    expect(h.actor.getSnapshot().matches({ reviewing: "yours" })).toBe(true);
    expect(h.calls.blobs[0]?.blob).toBe(
      h.actor.getSnapshot().context.recordings[0]?.blob,
    );
    h.actor.send({ type: "STOP" });
    expect(h.actor.getSnapshot().matches({ reviewing: "idle" })).toBe(true);

    h.actor.send({ type: "LISTEN_BOTH" });
    expect(h.actor.getSnapshot().matches({ reviewing: "both" })).toBe(true);
    expect(h.calls.boths[0]).toMatchObject({ segmentIndex: 0, rate: 1 });
  });

  it("LISTEN_YOURS từ idle bị bỏ qua khi câu chưa có bản ghi; có bản ghi thì phát được", async () => {
    const h = start();
    h.actor.send({ type: "LISTEN_YOURS" });
    h.actor.send({ type: "LISTEN_BOTH" });
    expect(h.actor.getSnapshot().matches("idle")).toBe(true);
    expect(h.calls.blobs).toHaveLength(0);
    expect(h.calls.boths).toHaveLength(0);

    await toReviewing(h);
    h.actor.send({ type: "GOTO", index: 0 });
    h.actor.send({ type: "LISTEN_YOURS" });
    expect(h.actor.getSnapshot().matches({ reviewing: "yours" })).toBe(true);
  });

  it("đang xử lý (scoring) vẫn nghe lại được bản ghi của mình (M)", () => {
    const h = start();
    h.ctl.upload = () => new Promise<AttemptAck>(() => {});
    const blob = toScoring(h);
    h.actor.send({ type: "LISTEN_YOURS" });
    expect(h.actor.getSnapshot().matches({ scoring: "yours" })).toBe(true);
    expect(h.calls.blobs[0]?.blob).toBe(blob);
    h.actor.send({ type: "STOP" });
    expect(h.actor.getSnapshot().matches({ scoring: "idle" })).toBe(true);
  });

  it("noVoice và error cũng nghe lại bản gốc/bản ghi (O, M)", async () => {
    const h = start();
    h.ctl.upload = async () => {
      throw new Error("x");
    };
    const blob = toScoring(h);
    await waitFor(h.actor, (s) => s.matches("error"));
    h.actor.send({ type: "LISTEN_YOURS" });
    expect(h.actor.getSnapshot().matches({ error: "yours" })).toBe(true);
    expect(h.calls.blobs[0]?.blob).toBe(blob);
  });

  it("playSample báo REP {n}: context.rep = n", () => {
    const h = start({ repeat: 3 });
    h.actor.send({ type: "PLAY" });
    h.ctl.sample?.({ type: "REP", n: 2 });
    expect(h.actor.getSnapshot().context.rep).toBe(2);
    h.ctl.sample?.({ type: "REP", n: 3 });
    expect(h.actor.getSnapshot().context.rep).toBe(3);
  });

  it("LEVEL từ recorder cập nhật context.level", () => {
    const h = start();
    toRecording(h);
    h.ctl.recorder?.({ type: "LEVEL", bars: 7, speech: true });
    expect(h.actor.getSnapshot().context.level).toEqual({
      bars: 7,
      speech: true,
    });
  });

  it("SET_RATE / SET_REPEAT / SET_RECORD_FACTOR đổi context ngoài recording/scoring; SEGMENTS_UPDATED thay độ dài câu", async () => {
    const h = start();
    h.actor.send({ type: "SET_RATE", rate: 0.75 });
    h.actor.send({ type: "SET_REPEAT", repeat: 2 });
    h.actor.send({ type: "SET_RECORD_FACTOR", recordFactor: 2 });
    let ctx = h.actor.getSnapshot().context;
    expect([ctx.rate, ctx.repeat, ctx.recordFactor]).toEqual([0.75, 2, 2]);

    h.actor.send({
      type: "SEGMENTS_UPDATED",
      segmentDurationsMs: [2300, 3000, 2500, 2000, 4000],
    });
    expect(h.actor.getSnapshot().context.segmentDurationsMs[0]).toBe(2300);

    toRecording(h);
    h.actor.send({ type: "SET_RATE", rate: 1 });
    h.actor.send({ type: "SET_REPEAT", repeat: 3 });
    h.actor.send({ type: "SET_RECORD_FACTOR", recordFactor: 1.25 });
    ctx = h.actor.getSnapshot().context;
    expect([ctx.rate, ctx.repeat, ctx.recordFactor]).toEqual([0.75, 2, 2]);
  });

  it("context không chứa điểm hay đánh giá đúng/sai (D-05, D-08)", async () => {
    const h = start();
    await toReviewing(h);
    const serialized = Object.keys(h.actor.getSnapshot().context).join(",");
    expect(serialized).not.toMatch(/score|grade|correct/i);
  });
});

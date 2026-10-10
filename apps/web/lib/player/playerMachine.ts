// Máy trạng thái phòng tập (PLY-02, ADR 0001). File này KHÔNG import React, DOM hay fetch:
// mọi tác dụng phụ là actor khai báo trong `setup`, UI/test thay bằng `playerMachine.provide`.
import { assign, fromCallback, fromPromise, sendTo, setup } from "xstate";
import type { ScoreResult } from "@shadowenglab/contracts";

export type RepeatCount = 1 | 2 | 3;

export type RecordingStatus = "pending" | "scored" | "noVoice" | "failed";

export interface PlayerRecording {
  blob: Blob;
  durationMs: number;
  status: RecordingStatus;
  attempt?: number;
  /** Kết quả chấm của lượt này; chỉ có khi `status === "scored"` (D-09). */
  result?: ScoreResult;
}

export interface PlayerLevel {
  /** 0..10 vạch sáng của LevelMeter */
  bars: number;
  speech: boolean;
}

export interface PlayerContext {
  segmentCount: number;
  segmentIndex: number;
  segmentDurationsMs: number[];
  repeat: RepeatCount;
  rate: number;
  recordFactor: number;
  /** Lần lặp hiện tại của câu mẫu (chip "lần i/n") */
  rep: number;
  recordings: Record<number, PlayerRecording>;
  lastError?: string;
  level: PlayerLevel;
}

export interface PlayerInput {
  segmentCount: number;
  startIndex: number;
  segmentDurationsMs: number[];
  repeat: RepeatCount;
  rate: number;
  recordFactor: number;
}

/** Sự kiện do UI/phím tắt gửi. */
export type PlayerUiEvent =
  | { type: "PLAY" }
  | { type: "STOP" }
  | { type: "RECORD" }
  | { type: "PREVIEW" }
  | { type: "NEXT" }
  | { type: "PREV" }
  | { type: "GOTO"; index: number }
  | { type: "LISTEN_ORIGINAL" }
  | { type: "LISTEN_YOURS" }
  | { type: "LISTEN_BOTH" }
  | { type: "RETRY_UPLOAD" }
  | { type: "SET_RATE"; rate: number }
  | { type: "SET_REPEAT"; repeat: RepeatCount }
  | { type: "SET_RECORD_FACTOR"; recordFactor: number }
  | { type: "SEGMENTS_UPDATED"; segmentDurationsMs: number[] };

/** Sự kiện do actor (phát mẫu, ghi âm) gửi ngược về machine. */
export type PlayerActorEvent =
  | { type: "REP"; n: number }
  | { type: "SAMPLE_DONE" }
  | { type: "SAMPLE_FAILED" }
  /** MediaRecorder đã chạy (sau khi micro mở xong, kể cả lúc chờ người dùng cấp quyền). */
  | { type: "RECORDING_STARTED" }
  | { type: "LEVEL"; bars: number; speech: boolean }
  | { type: "SILENCE" }
  | { type: "STOPPED"; blob: Blob; durationMs: number }
  | { type: "RECORD_FAILED"; reason: string };

export type PlayerEvent = PlayerUiEvent | PlayerActorEvent;

export interface PlaySampleInput {
  segmentIndex: number;
  repeat: RepeatCount;
  rate: number;
}
export interface PlayBlobInput {
  blob: Blob;
}
export interface PlayBothInput {
  segmentIndex: number;
  rate: number;
  blob: Blob;
}
export interface RecordInput {
  segmentIndex: number;
}
export interface UploadInput {
  segmentIndex: number;
  blob: Blob;
}

/** Trần thời gian ghi, khớp giới hạn 60 s của backend (RESEARCH Pattern 5b). */
const MAX_RECORD_MS = 60_000;

function currentRecording(context: PlayerContext): PlayerRecording | undefined {
  return context.recordings[context.segmentIndex];
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

/**
 * Lỗi `no_speech` của backend (HTTP 422, D-09): không có tiếng nói trong lượt vừa ghi.
 * Nhận dạng theo hình dạng `ApiRequestError.error.code` để file này không import api.ts.
 */
export function isNoSpeechError(error: unknown): boolean {
  if (typeof error !== "object" || error === null || !("error" in error)) {
    return false;
  }
  const inner = error.error;
  return (
    typeof inner === "object" &&
    inner !== null &&
    "code" in inner &&
    inner.code === "no_speech"
  );
}

const machineSetup = setup({
  types: {
    context: {} as PlayerContext,
    events: {} as PlayerEvent,
    input: {} as PlayerInput,
  },
  actors: {
    // Stub mặc định; UI thật và test thay bằng `playerMachine.provide({ actors })`.
    playSample: fromCallback<PlayerEvent, PlaySampleInput>(() => () => {}),
    playBlob: fromPromise<undefined, PlayBlobInput>(async () => undefined),
    playBoth: fromPromise<undefined, PlayBothInput>(async () => undefined),
    record: fromCallback<PlayerEvent, RecordInput>(() => () => {}),
    uploadAttempt: fromPromise<ScoreResult, UploadInput>(async () => {
      throw new Error("uploadAttempt actor chưa được cung cấp");
    }),
  },
  delays: {
    // Chỉ người dùng dừng ghi (nút "Dừng ghi" hoặc Space, Liam 2026-10-10); hẹn giờ này chỉ là trần
    // an toàn khớp giới hạn backend. recordFactor tạm không dùng (flows.md F2).
    recordDelay: MAX_RECORD_MS,
  },
  guards: {
    canNext: ({ context }) => context.segmentIndex < context.segmentCount - 1,
    canPrev: ({ context }) => context.segmentIndex > 0,
    validGoto: ({ context, event }) =>
      event.type === "GOTO" &&
      Number.isInteger(event.index) &&
      event.index >= 0 &&
      event.index < context.segmentCount,
    hasRecording: ({ context }) => currentRecording(context) !== undefined,
    hasScored: ({ context }) => currentRecording(context)?.status === "scored",
    hasNoVoice: ({ context }) =>
      currentRecording(context)?.status === "noVoice",
    hasFailed: ({ context }) => currentRecording(context)?.status === "failed",
  },
  actions: {
    goNext: assign({ segmentIndex: ({ context }) => context.segmentIndex + 1 }),
    goPrev: assign({ segmentIndex: ({ context }) => context.segmentIndex - 1 }),
    goTo: assign({
      segmentIndex: ({ context, event }) =>
        event.type === "GOTO" ? event.index : context.segmentIndex,
    }),
    resetRep: assign({ rep: 0 }),
    setRep: assign({
      rep: ({ context, event }) =>
        event.type === "REP" ? event.n : context.rep,
    }),
    resetLevel: assign({ level: { bars: 0, speech: false } }),
    setLevel: assign({
      level: ({ context, event }) =>
        event.type === "LEVEL"
          ? { bars: event.bars, speech: event.speech }
          : context.level,
    }),
    setRate: assign({
      rate: ({ context, event }) =>
        event.type === "SET_RATE" ? event.rate : context.rate,
    }),
    setRepeat: assign({
      repeat: ({ context, event }) =>
        event.type === "SET_REPEAT" ? event.repeat : context.repeat,
    }),
    setRecordFactor: assign({
      recordFactor: ({ context, event }) =>
        event.type === "SET_RECORD_FACTOR"
          ? event.recordFactor
          : context.recordFactor,
    }),
    setSegments: assign({
      segmentDurationsMs: ({ context, event }) =>
        event.type === "SEGMENTS_UPDATED"
          ? event.segmentDurationsMs
          : context.segmentDurationsMs,
    }),
    storeRecording: assign({
      recordings: ({ context, event }) =>
        event.type === "STOPPED"
          ? {
              ...context.recordings,
              [context.segmentIndex]: {
                blob: event.blob,
                durationMs: event.durationMs,
                status: "pending" as const,
              },
            }
          : context.recordings,
    }),
    markPending: assign({
      recordings: ({ context }) => {
        const rec = currentRecording(context);
        return rec
          ? {
              ...context.recordings,
              [context.segmentIndex]: { ...rec, status: "pending" as const },
            }
          : context.recordings;
      },
      lastError: undefined,
    }),
    micFailed: assign({ lastError: "mic" }),
    sampleFailed: assign({ lastError: "sample" }),
    stopRecorder: sendTo("recorder", { type: "STOP" }),
  },
});

/** Điều hướng câu: chỉ cho phép ở trạng thái không ghi và không xử lý (PLY-04). */
const navigation = {
  NEXT: { guard: "canNext", target: "#player.idle", actions: "goNext" },
  PREV: { guard: "canPrev", target: "#player.idle", actions: "goPrev" },
  GOTO: { guard: "validGoto", target: "#player.idle", actions: "goTo" },
} as const;

/** Đổi cài đặt phiên: chỉ ngoài recording/scoring. */
const settings = {
  SET_RATE: { actions: "setRate" },
  SET_REPEAT: { actions: "setRepeat" },
  SET_RECORD_FACTOR: { actions: "setRecordFactor" },
} as const;

/** Từ `idle`/`previewing`: về trạng thái đúng với bản ghi của câu hiện tại. */
const backToRecordingState = [
  { guard: "hasScored", target: "#player.reviewing" },
  { guard: "hasNoVoice", target: "#player.noVoice" },
  { guard: "hasFailed", target: "#player.error" },
  { target: "#player.idle" },
] as const;

const sampleInput = ({
  context,
}: {
  context: PlayerContext;
}): PlaySampleInput => ({
  segmentIndex: context.segmentIndex,
  repeat: 1,
  rate: context.rate,
});

const blobInput = ({ context }: { context: PlayerContext }): PlayBlobInput => {
  const rec = currentRecording(context);
  if (!rec) throw new Error("Không có bản ghi để phát");
  return { blob: rec.blob };
};

/** Các cách nghe lại ở reviewing / noVoice / error: bản gốc (O), của bạn (M), lần lượt (B). */
function listenStates() {
  return {
    initial: "idle",
    on: {
      LISTEN_ORIGINAL: { target: ".original" },
      LISTEN_YOURS: { guard: "hasRecording", target: ".yours" },
      LISTEN_BOTH: { guard: "hasRecording", target: ".both" },
    },
    states: {
      idle: {},
      original: {
        invoke: { src: "playSample", input: sampleInput },
        on: { SAMPLE_DONE: "idle", SAMPLE_FAILED: "idle", STOP: "idle" },
      },
      yours: {
        invoke: {
          src: "playBlob",
          input: blobInput,
          onDone: "idle",
          onError: "idle",
        },
        on: { STOP: "idle" },
      },
      both: {
        invoke: {
          src: "playBoth",
          input: ({ context }: { context: PlayerContext }): PlayBothInput => ({
            segmentIndex: context.segmentIndex,
            rate: context.rate,
            blob: blobInput({ context }).blob,
          }),
          onDone: "idle",
          onError: "idle",
        },
        on: { STOP: "idle" },
      },
    },
  } as const;
}

export const playerMachine = machineSetup.createMachine({
  id: "player",
  initial: "idle",
  context: ({ input }) => ({
    segmentCount: input.segmentCount,
    segmentIndex: input.startIndex,
    segmentDurationsMs: input.segmentDurationsMs,
    repeat: input.repeat,
    rate: input.rate,
    recordFactor: input.recordFactor,
    rep: 0,
    recordings: {},
    level: { bars: 0, speech: false },
  }),
  on: {
    // Dùng sau "Mất chữ cuối?" ở mọi trạng thái; recordDelay đã hẹn không bị đổi giữa chừng.
    SEGMENTS_UPDATED: { actions: "setSegments" },
  },
  states: {
    idle: {
      on: {
        ...navigation,
        ...settings,
        PLAY: "playing",
        PREVIEW: "previewing",
        RECORD: "recording",
        LISTEN_YOURS: [
          { guard: "hasScored", target: "#player.reviewing.yours" },
          { guard: "hasNoVoice", target: "#player.noVoice.yours" },
          { guard: "hasFailed", target: "#player.error.yours" },
        ],
        LISTEN_BOTH: [
          { guard: "hasScored", target: "#player.reviewing.both" },
          { guard: "hasNoVoice", target: "#player.noVoice.both" },
          { guard: "hasFailed", target: "#player.error.both" },
        ],
      },
    },
    previewing: {
      // O: phát mẫu một lần, không ghi tiếp.
      invoke: { src: "playSample", input: sampleInput },
      entry: "resetRep",
      on: {
        ...navigation,
        ...settings,
        REP: { actions: "setRep" },
        STOP: "idle",
        SAMPLE_DONE: backToRecordingState,
        SAMPLE_FAILED: { target: "idle", actions: "sampleFailed" },
      },
    },
    playing: {
      // Space: phát mẫu x repeat rồi tự chuyển sang ghi.
      entry: "resetRep",
      invoke: {
        src: "playSample",
        input: ({ context }) => ({
          segmentIndex: context.segmentIndex,
          repeat: context.repeat,
          rate: context.rate,
        }),
      },
      on: {
        ...navigation,
        ...settings,
        REP: { actions: "setRep" },
        STOP: "idle",
        SAMPLE_DONE: "recording",
        SAMPLE_FAILED: { target: "idle", actions: "sampleFailed" },
      },
    },
    recording: {
      entry: "resetLevel",
      invoke: {
        id: "recorder",
        src: "record",
        input: ({ context }) => ({ segmentIndex: context.segmentIndex }),
      },
      // Hẹn giờ tự dừng chỉ chạy từ lúc MediaRecorder thật sự bắt đầu: lần đầu trình duyệt hỏi
      // quyền micro có thể mất lâu hơn recordDelay, khi đó clip sẽ gần như rỗng.
      initial: "opening",
      states: {
        opening: { on: { RECORDING_STARTED: "active" } },
        active: { after: { recordDelay: { actions: "stopRecorder" } } },
      },
      on: {
        STOP: { actions: "stopRecorder" },
        LEVEL: { actions: "setLevel" },
        STOPPED: { target: "scoring", actions: "storeRecording" },
        RECORD_FAILED: { target: "error", actions: "micFailed" },
      },
    },
    scoring: {
      // Phase 3: chấm trong cùng request tải lên; actor trả ScoreResult (D-09, hình machine không đổi).
      invoke: {
        src: "uploadAttempt",
        input: ({ context }) => {
          const rec = currentRecording(context);
          if (!rec) throw new Error("Không có bản ghi để tải lên");
          return { segmentIndex: context.segmentIndex, blob: rec.blob };
        },
        onDone: {
          target: "reviewing",
          actions: assign({
            recordings: ({ context, event }) => {
              const rec = currentRecording(context);
              return rec
                ? {
                    ...context.recordings,
                    [context.segmentIndex]: {
                      ...rec,
                      status: "scored" as const,
                      attempt: event.output.attempt,
                      result: event.output,
                    },
                  }
                : context.recordings;
            },
          }),
        },
        onError: [
          {
            guard: ({ event }) => isNoSpeechError(event.error),
            target: "noVoice",
            actions: assign({
              recordings: ({ context }) => {
                const rec = currentRecording(context);
                return rec
                  ? {
                      ...context.recordings,
                      [context.segmentIndex]: {
                        ...rec,
                        status: "noVoice" as const,
                      },
                    }
                  : context.recordings;
              },
            }),
          },
          {
            target: "error",
            actions: assign({
              lastError: ({ event }) => errorMessage(event.error),
              recordings: ({ context }) => {
                const rec = currentRecording(context);
                return rec
                  ? {
                      ...context.recordings,
                      [context.segmentIndex]: {
                        ...rec,
                        status: "failed" as const,
                      },
                    }
                  : context.recordings;
              },
            }),
          },
        ],
      },
      // Vẫn nghe lại bản ghi của mình trong lúc xử lý (M).
      initial: "idle",
      states: {
        idle: {
          on: { LISTEN_YOURS: { guard: "hasRecording", target: "yours" } },
        },
        yours: {
          invoke: {
            src: "playBlob",
            input: blobInput,
            onDone: "idle",
            onError: "idle",
          },
          on: { STOP: "idle" },
        },
      },
    },
    reviewing: {
      ...listenStates(),
      on: {
        ...listenStates().on,
        ...navigation,
        ...settings,
        PLAY: "playing",
        RECORD: "recording",
      },
    },
    noVoice: {
      ...listenStates(),
      on: {
        ...listenStates().on,
        ...navigation,
        ...settings,
        PLAY: "playing",
        RECORD: "recording",
      },
    },
    error: {
      ...listenStates(),
      on: {
        ...listenStates().on,
        ...navigation,
        ...settings,
        PLAY: "playing",
        RECORD: "recording",
        RETRY_UPLOAD: {
          guard: "hasFailed",
          target: "scoring",
          actions: "markPending",
        },
      },
    },
  },
});

export type PlayerMachine = typeof playerMachine;

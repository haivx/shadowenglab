// Máy trạng thái phòng tập (PLY-02, ADR 0001). File này KHÔNG import React, DOM hay fetch:
// mọi tác dụng phụ là actor khai báo trong `setup`, UI/test thay bằng `playerMachine.provide`.
import { fromCallback, fromPromise, setup } from "xstate";
import type { AttemptAck } from "@shadowenglab/contracts";

export type RepeatCount = 1 | 2 | 3;

export type RecordingStatus = "pending" | "uploaded" | "noVoice" | "failed";

export interface PlayerRecording {
  blob: Blob;
  durationMs: number;
  status: RecordingStatus;
  attempt?: number;
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

export const playerMachine = setup({
  types: {
    context: {} as PlayerContext,
    events: {} as PlayerEvent,
    input: {} as PlayerInput,
  },
  actors: {
    playSample: fromCallback<PlayerEvent, PlaySampleInput>(() => () => {}),
    playBlob: fromPromise<void, PlayBlobInput>(async () => {}),
    playBoth: fromPromise<void, PlayBothInput>(async () => {}),
    record: fromCallback<PlayerEvent, RecordInput>(() => () => {}),
    uploadAttempt: fromPromise<AttemptAck, UploadInput>(async () => {
      throw new Error("uploadAttempt actor chưa được cung cấp");
    }),
  },
}).createMachine({
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
  states: {
    idle: {},
  },
});

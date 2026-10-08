// Actor ghi âm của phòng tập (REC-01, RESEARCH Pattern 5a). Bản ghi chỉ nằm trong bộ nhớ trình
// duyệt (Blob gửi về machine), không ghi vào localStorage/IndexedDB (D-07, T-02-39).
// Micro, AudioContext và rAF được đóng ở MỌI đường thoát (T-02-40), kể cả khi StrictMode
// mount rồi unmount actor trước khi micro kịp mở.
import { fromCallback } from "xstate";
import type { PlayerEvent, RecordInput } from "../player/playerMachine";
import { browserRaf, type RafLike } from "../player/playRange";
import { createLevelState, updateLevel } from "./level";
import { pickMimeType } from "./mime";

/** Khoá localStorage lưu id micro đã chọn ở S8 (không nằm trong AppSettings, UI-SPEC S8). */
export const MIC_DEVICE_STORAGE_KEY = "shadowenglab.micDeviceId";

const FFT_SIZE = 2048;

export interface MicHandle {
  stream: MediaStream;
  analyser: {
    fftSize: number;
    getFloatTimeDomainData(array: Float32Array<ArrayBuffer>): void;
  };
  /** Dừng mọi track và đóng AudioContext. Gọi nhiều lần vẫn an toàn. */
  close(): void;
}

/**
 * Mở micro ở chế độ thô: tắt khử vọng, khử ồn và tự chỉnh gain để mức âm và độ lớn phản ánh
 * đúng giọng người học. `deviceId` chỉ là gợi ý (`ideal`): thiết bị đã rút thì rơi về mặc định.
 */
export async function openMic(deviceId?: string): Promise<MicHandle> {
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: {
      deviceId: deviceId ? { ideal: deviceId } : undefined,
      echoCancellation: false,
      noiseSuppression: false,
      autoGainControl: false,
      channelCount: 1,
    },
  });

  let context: AudioContext | undefined;
  let closed = false;
  const close = () => {
    if (closed) return;
    closed = true;
    for (const track of stream.getTracks()) track.stop();
    if (context && context.state !== "closed") {
      context.close().catch(() => undefined);
    }
  };

  try {
    context = new AudioContext();
    const analyser = context.createAnalyser();
    analyser.fftSize = FFT_SIZE;
    context.createMediaStreamSource(stream).connect(analyser);
    // Không nối analyser vào destination: nghe lại chính mình khi đang nói sẽ gây vọng.
    void context.resume().catch(() => undefined);
    return { stream, analyser, close };
  } catch (error) {
    close();
    throw error;
  }
}

export interface RecorderLike {
  mimeType: string;
  state: string;
  start(): void;
  stop(): void;
  onData(callback: (data: Blob) => void): void;
  onStop(callback: () => void): void;
  onError(callback: () => void): void;
}

function browserRecorder(
  stream: MediaStream,
  mimeType: string | undefined,
): RecorderLike {
  const recorder = new MediaRecorder(
    stream,
    mimeType ? { mimeType } : undefined,
  );
  return {
    get mimeType() {
      return recorder.mimeType;
    },
    get state() {
      return recorder.state;
    },
    start: () => recorder.start(),
    stop: () => recorder.stop(),
    onData: (callback) =>
      recorder.addEventListener("dataavailable", (event) =>
        callback(event.data),
      ),
    onStop: (callback) => recorder.addEventListener("stop", callback),
    onError: (callback) => recorder.addEventListener("error", callback),
  };
}

function readSavedDeviceId(): string | undefined {
  try {
    return window.localStorage.getItem(MIC_DEVICE_STORAGE_KEY) ?? undefined;
  } catch {
    return undefined;
  }
}

/** Phụ thuộc trình duyệt của actor, đưa vào được để test bằng đối tượng giả trong node. */
export interface RecordDeps {
  openMic: (deviceId?: string) => Promise<MicHandle>;
  createRecorder: (
    stream: MediaStream,
    mimeType: string | undefined,
  ) => RecorderLike;
  isTypeSupported: (type: string) => boolean;
  readDeviceId: () => string | undefined;
  raf: RafLike;
  now: () => number;
}

const browserDeps: RecordDeps = {
  openMic,
  createRecorder: browserRecorder,
  isTypeSupported: (type) => MediaRecorder.isTypeSupported(type),
  readDeviceId: readSavedDeviceId,
  raf: browserRaf,
  now: () => performance.now(),
};

/**
 * Actor `record` của playerMachine (id `recorder`). Nhận `STOP` từ machine; gửi `RECORDING_STARTED`
 * khi MediaRecorder bắt đầu chạy, `LEVEL` mỗi khi mức đổi, `SILENCE` đúng một lần khi im lặng sau tiếng nói, `STOPPED {blob, durationMs}` khi ghi
 * xong và `RECORD_FAILED` khi không mở được micro hoặc MediaRecorder lỗi.
 */
export function makeRecordActor(overrides: Partial<RecordDeps> = {}) {
  const deps: RecordDeps = { ...browserDeps, ...overrides };

  return fromCallback<PlayerEvent, RecordInput>(({ sendBack, receive }) => {
    let disposed = false;
    let stopRequested = false;
    let mic: MicHandle | undefined;
    let recorder: RecorderLike | undefined;
    let rafId: number | null = null;
    let startedAt = 0;
    const chunks: Blob[] = [];

    const stopLoop = () => {
      if (rafId !== null) {
        deps.raf.cancel(rafId);
        rafId = null;
      }
    };
    const releaseMic = () => {
      stopLoop();
      mic?.close();
    };

    const requestStop = () => {
      stopRequested = true;
      if (recorder && recorder.state === "recording") recorder.stop();
    };

    receive((event) => {
      if (event.type === "STOP") requestStop();
    });

    function startLevelLoop(handle: MicHandle) {
      const buffer = new Float32Array(handle.analyser.fftSize);
      let state = createLevelState();
      let lastTime = deps.now();
      let lastBars = -1;
      let lastSpeech = false;
      let silenceSent = false;

      const tick = () => {
        rafId = null;
        if (disposed) return;
        const time = deps.now();
        const dtMs = Math.max(0, time - lastTime);
        lastTime = time;

        handle.analyser.getFloatTimeDomainData(buffer);
        state = updateLevel(state, buffer, dtMs);

        if (state.bars !== lastBars || state.speech !== lastSpeech) {
          lastBars = state.bars;
          lastSpeech = state.speech;
          sendBack({ type: "LEVEL", bars: state.bars, speech: state.speech });
        }
        if (state.silenceDetected && !silenceSent) {
          silenceSent = true;
          sendBack({ type: "SILENCE" });
        }
        rafId = deps.raf.request(tick);
      };
      rafId = deps.raf.request(tick);
    }

    async function run() {
      let handle: MicHandle;
      try {
        handle = await deps.openMic(deps.readDeviceId());
      } catch {
        if (!disposed) sendBack({ type: "RECORD_FAILED", reason: "mic" });
        return;
      }
      mic = handle;
      // Actor đã bị dọn trong lúc chờ quyền micro (rời trạng thái, StrictMode): trả micro ngay.
      if (disposed) {
        releaseMic();
        return;
      }

      try {
        const mimeType = pickMimeType(deps.isTypeSupported);
        const created = deps.createRecorder(handle.stream, mimeType);
        recorder = created;
        created.onData((data) => {
          if (data.size > 0) chunks.push(data);
        });
        created.onStop(() => {
          const durationMs = Math.round(deps.now() - startedAt);
          releaseMic();
          if (disposed) return;
          const blob = new Blob(chunks, {
            type: created.mimeType || mimeType || "audio/webm",
          });
          sendBack({ type: "STOPPED", blob, durationMs });
        });
        created.onError(() => {
          releaseMic();
          if (!disposed)
            sendBack({ type: "RECORD_FAILED", reason: "recorder" });
        });
        startedAt = deps.now();
        created.start();
        startLevelLoop(handle);
        // Machine chỉ hẹn giờ tự dừng từ lúc này, không tính thời gian chờ cấp quyền micro.
        sendBack({ type: "RECORDING_STARTED" });
        // STOP tới trước khi micro mở xong (Space bấm rất sớm): dừng ngay khi đã chạy.
        if (stopRequested) requestStop();
      } catch {
        releaseMic();
        if (!disposed) sendBack({ type: "RECORD_FAILED", reason: "recorder" });
      }
    }

    void run();

    return () => {
      disposed = true;
      stopLoop();
      if (recorder && recorder.state !== "inactive") {
        try {
          recorder.stop();
        } catch {
          // đã dừng: không còn gì để làm
        }
      }
      releaseMic();
    };
  });
}

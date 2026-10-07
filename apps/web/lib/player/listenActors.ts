// Actor nghe lại ở reviewing / noVoice / error / scoring (PLY-07): `Của bạn` phát bản ghi trong bộ nhớ,
// `Lần lượt cả hai` phát bản gốc một lần rồi bản ghi. Bản ghi không bao giờ rời bộ nhớ trình duyệt
// (D-07, T-02-39): object URL được thu hồi ở mọi đường thoát.
import { fromPromise } from "xstate";
import type { PlayBlobInput, PlayBothInput } from "./playerMachine";
import {
  browserRaf,
  isAbortError,
  playRange,
  sampleWindow,
  type PlayableLesson,
  type RafLike,
  type VideoLike,
} from "./playRange";

/** Phần của phần tử audio mà việc phát lại cần. */
export interface AudioLike {
  play(): Promise<void>;
  pause(): void;
  onended: (() => void) | null;
  onerror: (() => void) | null;
}

export interface BlobPlaybackDeps {
  createUrl: (blob: Blob) => string;
  revokeUrl: (url: string) => void;
  createAudio: (url: string) => AudioLike;
}

function browserAudio(url: string): AudioLike {
  const audio = new Audio(url);
  return {
    play: () => audio.play(),
    pause: () => audio.pause(),
    set onended(handler: (() => void) | null) {
      audio.onended = handler;
    },
    get onended() {
      return audio.onended as (() => void) | null;
    },
    set onerror(handler: (() => void) | null) {
      audio.onerror = handler;
    },
    get onerror() {
      return audio.onerror as (() => void) | null;
    },
  };
}

const browserBlobDeps: BlobPlaybackDeps = {
  createUrl: (blob) => URL.createObjectURL(blob),
  revokeUrl: (url) => URL.revokeObjectURL(url),
  createAudio: browserAudio,
};

/**
 * Phát một Blob tới hết. Resolve khi `ended`; reject khi lỗi giải mã/phát hoặc `signal` bị huỷ
 * (rời trạng thái → pause). Luôn thu hồi object URL.
 */
export function playBlobOnce(
  blob: Blob,
  signal: AbortSignal,
  deps: BlobPlaybackDeps = browserBlobDeps,
): Promise<void> {
  return new Promise<void>((resolve, reject) => {
    if (signal.aborted) {
      reject(new DOMException("aborted", "AbortError"));
      return;
    }
    const url = deps.createUrl(blob);
    const audio = deps.createAudio(url);
    let settled = false;

    const finish = (error?: unknown) => {
      if (settled) return;
      settled = true;
      signal.removeEventListener("abort", onAbort);
      audio.onended = null;
      audio.onerror = null;
      deps.revokeUrl(url);
      if (error === undefined) resolve();
      else reject(error);
    };
    const onAbort = () => {
      audio.pause();
      finish(new DOMException("aborted", "AbortError"));
    };

    signal.addEventListener("abort", onAbort, { once: true });
    audio.onended = () => finish();
    audio.onerror = () => finish(new Error("Không phát được bản ghi"));
    audio.play().catch((error: unknown) => {
      audio.pause();
      finish(error);
    });
  });
}

/** Actor `playBlob` của machine: `Của bạn` (M). */
export function makePlayBlob(deps?: BlobPlaybackDeps) {
  return fromPromise<undefined, PlayBlobInput>(async ({ input, signal }) => {
    await playBlobOnce(input.blob, signal, deps);
    return undefined;
  });
}

export type PlayOriginalOnce = (
  segmentIndex: number,
  rate: number,
  signal: AbortSignal,
) => Promise<void>;

/**
 * Phát câu mẫu một lần bằng video tự host, cùng cửa sổ phát (pad + nới câu) với `makePlaySample`.
 * Đọc video và bài qua getter nên luôn thấy dữ liệu mới nhất.
 */
export function makePlayOriginalOnce(
  getVideo: () => VideoLike | null,
  getLesson: () => PlayableLesson | undefined,
  raf: RafLike = browserRaf,
): PlayOriginalOnce {
  return async (segmentIndex, rate, signal) => {
    const video = getVideo();
    const lesson = getLesson();
    const segment = lesson?.segments[segmentIndex];
    if (!video || !lesson || !segment) {
      throw new Error("Không có video để phát bản gốc");
    }
    const videoDuration =
      video.duration !== undefined && Number.isFinite(video.duration)
        ? video.duration
        : lesson.durationSec;
    const { startS, endS } = sampleWindow(
      segment,
      lesson.padMs,
      Math.min(lesson.durationSec, videoDuration),
    );
    await playRange(video, startS, endS, rate, signal, raf);
  };
}

/**
 * Actor `playBoth` của machine: `Lần lượt cả hai` (B) = bản gốc một lần rồi bản của bạn.
 * Huỷ giữa chừng (STOP, chuyển câu) dừng cả hai đoạn; lỗi phát khiến machine về idle.
 */
export function makePlayBoth(
  playOriginalOnce: PlayOriginalOnce,
  deps?: BlobPlaybackDeps,
) {
  return fromPromise<undefined, PlayBothInput>(async ({ input, signal }) => {
    try {
      await playOriginalOnce(input.segmentIndex, input.rate, signal);
      await playBlobOnce(input.blob, signal, deps);
    } catch (error) {
      // Huỷ có chủ đích không phải lỗi; machine đã rời trạng thái nên kết quả bị bỏ qua.
      if (!isAbortError(error)) throw error;
    }
    return undefined;
  });
}

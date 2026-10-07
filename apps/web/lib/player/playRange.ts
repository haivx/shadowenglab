// Phát chính xác đoạn một câu từ video tự host (PLY-03, RESEARCH Pattern 4).
// Dừng bằng vòng requestAnimationFrame so `currentTime` với mốc cuối, không nghe sự kiện cập nhật
// thời gian của video (RESEARCH A8: quá thưa so với biên đệm 100–200 ms). Mọi phụ thuộc trình duyệt đi qua
// kiểu cấu trúc `VideoLike` / `RafLike` để test bằng video giả trong môi trường node.
import { fromCallback } from "xstate";
import type { Segment } from "@shadowenglab/contracts";
import type { PlaySampleInput, PlayerEvent } from "./playerMachine";

export interface VideoLike {
  currentTime: number;
  playbackRate: number;
  play(): Promise<void>;
  pause(): void;
  /** Tổng thời lượng (giây); vắng mặt hoặc không hữu hạn thì không kẹp theo video. */
  duration?: number;
  /** Video đã tự chạy tới cuối file thì dừng, kể cả khi `currentTime` chưa chạm mốc. */
  ended?: boolean;
  /** Giữ cao độ khi đổi tốc độ (0.75x). Mặc định true ở trình duyệt hiện đại. */
  preservesPitch?: boolean;
}

export interface RafLike {
  request(callback: (timeMs: number) => void): number;
  cancel(id: number): void;
}

/** Cầu nối tới requestAnimationFrame của trình duyệt (gọi trễ để không đụng window khi import ở node). */
export const browserRaf: RafLike = {
  request: (callback) => requestAnimationFrame(callback),
  cancel: (id) => cancelAnimationFrame(id),
};

/** Nghỉ ngắn giữa các lần lặp để người nghe tách được từng lần (RESEARCH Pattern 4). */
export const REPEAT_GAP_MS = 300;

/** Phần của Segment dùng để tính cửa sổ phát. */
export type SampleSegment = Pick<Segment, "start" | "end" | "endExtraMs">;

export interface SampleWindow {
  startS: number;
  endS: number;
}

/**
 * Cửa sổ phát câu mẫu: [start − pad, end + pad + endExtraMs], kẹp trong [0, thời lượng video].
 * `endExtraMs` là phần người dùng đã nới bằng "Mất chữ cuối?" (quyết định E).
 */
export function sampleWindow(
  segment: SampleSegment,
  padMs: number,
  durationSec: number,
): SampleWindow {
  const maxEnd = Math.max(0, durationSec);
  const startS = Math.min(Math.max(0, segment.start - padMs / 1000), maxEnd);
  const endS = Math.min(
    Math.max(startS, segment.end + padMs / 1000 + segment.endExtraMs / 1000),
    maxEnd,
  );
  return { startS, endS };
}

function abortError(): DOMException {
  return new DOMException("aborted", "AbortError");
}

export function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

/**
 * Phát video từ `startS` tới `endS` ở tốc độ `rate`. Resolve khi `currentTime` chạm `endS`
 * (sai số tối đa một khung hình). `signal` bị huỷ: dừng rAF, pause, reject AbortError.
 * Từ chối `play()` (autoplay policy, file hỏng) được chuyển thành reject.
 */
export function playRange(
  video: VideoLike,
  startS: number,
  endS: number,
  rate: number,
  signal: AbortSignal,
  raf: RafLike = browserRaf,
): Promise<void> {
  return new Promise<void>((resolve, reject) => {
    if (signal.aborted) {
      reject(abortError());
      return;
    }

    let rafId: number | null = null;
    let settled = false;

    const cancelFrame = () => {
      if (rafId !== null) {
        raf.cancel(rafId);
        rafId = null;
      }
    };

    const finish = (error?: unknown) => {
      if (settled) return;
      settled = true;
      cancelFrame();
      signal.removeEventListener("abort", onAbort);
      if (error === undefined) resolve();
      else reject(error);
    };

    const onAbort = () => {
      video.pause();
      finish(abortError());
    };
    signal.addEventListener("abort", onAbort, { once: true });

    const tick = () => {
      rafId = null;
      if (settled) return;
      if (video.currentTime >= endS || video.ended === true) {
        video.pause();
        finish();
        return;
      }
      rafId = raf.request(tick);
    };

    video.currentTime = startS;
    video.playbackRate = rate;
    video.preservesPitch = true;
    // Vòng dừng chạy ngay sau khi gọi play(): từ chối của play() sẽ dừng nó qua `finish`.
    const started = video.play();
    rafId = raf.request(tick);
    started.catch((error: unknown) => {
      video.pause();
      finish(error);
    });
  });
}

/** Cho phép đổi bộ hẹn giờ khi test. */
export interface PlaySampleOptions {
  gapMs?: number;
  wait?: (ms: number, signal: AbortSignal) => Promise<void>;
}

/** Dữ liệu bài mà actor cần tại thời điểm phát (đọc lại mỗi lần, vì câu có thể được nới). */
export interface PlayableLesson {
  segments: SampleSegment[];
  padMs: number;
  durationSec: number;
}

function defaultWait(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise<void>((resolve, reject) => {
    if (signal.aborted) {
      reject(abortError());
      return;
    }
    const onAbort = () => {
      clearTimeout(timer);
      reject(abortError());
    };
    const timer = setTimeout(() => {
      signal.removeEventListener("abort", onAbort);
      resolve();
    }, ms);
    signal.addEventListener("abort", onAbort, { once: true });
  });
}

/**
 * Actor `playSample` thật cho playerMachine: phát câu `repeat` lần, mỗi lần seek về đầu cửa sổ,
 * nghỉ `gapMs` giữa các lần. Gửi `REP {n}` trước mỗi lần, `SAMPLE_DONE` khi xong,
 * `SAMPLE_FAILED` nếu play() bị từ chối hoặc thiếu video/câu. Cleanup (rời trạng thái) huỷ rAF và pause.
 */
export function makePlaySample(
  getVideo: () => VideoLike | null,
  getLesson: () => PlayableLesson | undefined,
  raf: RafLike = browserRaf,
  options: PlaySampleOptions = {},
) {
  const gapMs = options.gapMs ?? REPEAT_GAP_MS;
  const wait = options.wait ?? defaultWait;

  return fromCallback<PlayerEvent, PlaySampleInput>(({ input, sendBack }) => {
    const controller = new AbortController();
    const video = getVideo();

    async function run(): Promise<void> {
      const lesson = getLesson();
      const segment = lesson?.segments[input.segmentIndex];
      if (!video || !lesson || !segment) {
        sendBack({ type: "SAMPLE_FAILED" });
        return;
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

      try {
        for (let n = 1; n <= input.repeat; n += 1) {
          sendBack({ type: "REP", n });
          await playRange(
            video,
            startS,
            endS,
            input.rate,
            controller.signal,
            raf,
          );
          if (n < input.repeat) await wait(gapMs, controller.signal);
        }
        sendBack({ type: "SAMPLE_DONE" });
      } catch (error) {
        if (controller.signal.aborted || isAbortError(error)) return;
        sendBack({ type: "SAMPLE_FAILED" });
      }
    }

    void run();

    return () => {
      controller.abort();
      video?.pause();
    };
  });
}

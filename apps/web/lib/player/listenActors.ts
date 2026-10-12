// Actor nghe lại ở reviewing / noVoice / error / scoring (PLY-07): `Của bạn` phát bản ghi trong bộ nhớ,
// `Lần lượt cả hai` phát bản gốc một lần rồi bản ghi. Bản ghi không bao giờ rời bộ nhớ trình duyệt
// (D-07, T-02-39): AudioContext được đóng ở mọi đường thoát. Bản ghi thô (tắt AGC/NS/AEC để chấm
// điểm) thường nhỏ hơn audio YouTube nên khi NGHE LẠI được chuẩn hoá âm lượng bằng Web Audio;
// Blob gửi đi chấm giữ nguyên.
import { fromPromise } from "xstate";
import { playbackGain } from "../audio/playbackGain";
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

/** Nguồn phát đã nối vào đồ thị âm thanh. */
export interface SourceLike {
  onended: (() => void) | null;
  start(): Promise<void>;
  stop(): void;
}

/** Bản ghi đã giải mã: các kênh mẫu và cách nối vào loa qua một gain. */
export interface DecodedLike {
  channels: readonly Float32Array[];
  connect(gain: number): SourceLike;
}

export interface PlaybackContextLike {
  decode(data: ArrayBuffer): Promise<DecodedLike>;
  close(): void;
}

export interface BlobPlaybackDeps {
  readBlob: (blob: Blob) => Promise<ArrayBuffer>;
  createContext: () => PlaybackContextLike;
}

/**
 * Adapter trình duyệt: source -> GainNode -> DynamicsCompressorNode (limiter) -> loa.
 * Mỗi lượt phát dùng một AudioContext mới, đóng khi xong.
 */
function browserPlaybackContext(): PlaybackContextLike {
  const context = new AudioContext();
  let closed = false;
  return {
    async decode(data) {
      const buffer = await context.decodeAudioData(data);
      const channels: Float32Array[] = [];
      for (let i = 0; i < buffer.numberOfChannels; i += 1) {
        channels.push(buffer.getChannelData(i));
      }
      return {
        channels,
        connect(gain) {
          const source = context.createBufferSource();
          source.buffer = buffer;
          const gainNode = context.createGain();
          gainNode.gain.value = gain;
          // Limiter đặt tường minh: mặc định (threshold -24, knee 30, ratio 12) sẽ nén mạnh giọng nói.
          const limiter = context.createDynamicsCompressor();
          limiter.threshold.value = -1;
          limiter.knee.value = 0;
          limiter.ratio.value = 20;
          limiter.attack.value = 0.003;
          limiter.release.value = 0.1;
          source.connect(gainNode);
          gainNode.connect(limiter);
          limiter.connect(context.destination);
          return {
            set onended(handler: (() => void) | null) {
              source.onended = handler;
            },
            get onended() {
              return source.onended as (() => void) | null;
            },
            async start() {
              await context.resume();
              source.start();
            },
            stop() {
              try {
                source.stop();
              } catch {
                // stop() trước start() ném InvalidStateError; bỏ qua.
              }
            },
          };
        },
      };
    },
    close() {
      if (closed) return;
      closed = true;
      if (context.state !== "closed") {
        context.close().catch(() => undefined);
      }
    },
  };
}

const browserBlobDeps: BlobPlaybackDeps = {
  // `arrayBuffer()` trả BẢN SAO mới mỗi lần; decodeAudioData detach buffer truyền vào nên không
  // được cache hay dùng lại, và không bao giờ ghi vào Blob (Blob gửi chấm và "Lưu clip cho eval").
  readBlob: (blob) => blob.arrayBuffer(),
  createContext: browserPlaybackContext,
};

/**
 * Phát một Blob tới hết với âm lượng đã chuẩn hoá. Resolve khi phát xong; reject khi lỗi đọc/giải
 * mã/phát hoặc `signal` bị huỷ (rời trạng thái → dừng nguồn). AudioContext luôn được đóng đúng một lần.
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
    // Tạo context đồng bộ, còn trong cử chỉ bấm nút (chính sách autoplay).
    const context = deps.createContext();
    let source: SourceLike | undefined;
    let settled = false;

    const finish = (error?: unknown) => {
      if (settled) return;
      settled = true;
      signal.removeEventListener("abort", onAbort);
      if (source) {
        source.onended = null;
        if (error !== undefined) source.stop();
      }
      context.close();
      if (error === undefined) resolve();
      else reject(error);
    };
    const onAbort = () => finish(new DOMException("aborted", "AbortError"));

    signal.addEventListener("abort", onAbort, { once: true });

    void (async () => {
      let started: SourceLike;
      try {
        const data = await deps.readBlob(blob);
        if (settled) return;
        const decoded = await context.decode(data);
        if (settled) return;
        started = decoded.connect(playbackGain(decoded.channels));
      } catch {
        finish(new Error("Không phát được bản ghi"));
        return;
      }
      source = started;
      started.onended = () => finish();
      started.start().catch((error: unknown) => finish(error));
    })();
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

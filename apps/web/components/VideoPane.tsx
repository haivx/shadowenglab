"use client";

import { useMutation } from "@tanstack/react-query";
import { useCallback, useEffect, useState, type RefObject } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { lessonVideoUrl, reloadLessonVideo } from "@/lib/api";
import { showSentenceFrame } from "@/lib/player/playRange";

/** `mm:ss.s` cho lớp phủ khoảng thời gian của câu (UI-SPEC S3 Video). */
export function formatClockTenths(seconds: number): string {
  const tenths = Math.max(0, Math.floor(seconds * 10));
  const minutes = Math.floor(tenths / 600);
  const secs = Math.floor((tenths % 600) / 10);
  const tenth = tenths % 10;
  return `${String(minutes).padStart(2, "0")}:${String(secs).padStart(2, "0")}.${tenth}`;
}

type VideoStatus = "loading" | "ready" | "error";

interface VideoPaneProps {
  lessonId: string;
  /** PracticeRoom đọc phần tử này qua ref để phát đoạn câu mẫu. */
  videoRef: RefObject<HTMLVideoElement>;
  startSec: number;
  endSec: number;
  /** Số thứ tự câu hiển thị (bắt đầu từ 1). */
  sentenceNumber: number;
  /** true khi video đã bắn `canplay`; false khi đang nạp hoặc lỗi. */
  onReadyChange: (ready: boolean) => void;
}

/**
 * Video tự host 16:9, không điều khiển gốc (PLY-01, D-17). Không có YouTube IFrame.
 * Thiếu file hoặc lỗi giải mã/mạng: `Không phát được video của bài này.` + `Tải lại video`.
 */
export function VideoPane({
  lessonId,
  videoRef,
  startSec,
  endSec,
  sentenceNumber,
  onReadyChange,
}: VideoPaneProps) {
  const [status, setStatus] = useState<VideoStatus>("loading");
  // Sau `Tải lại video` thêm tham số chống cache để trình duyệt lấy lại file.
  const [nonce, setNonce] = useState<number | null>(null);

  const updateStatus = useCallback(
    (next: VideoStatus) => {
      setStatus(next);
      onReadyChange(next === "ready");
    },
    [onReadyChange],
  );

  // `canplay` có thể đã bắn trước khi React gắn listener (video lấy từ cache).
  useEffect(() => {
    const video = videoRef.current;
    if (video && video.readyState >= HTMLMediaElement.HAVE_FUTURE_DATA) {
      updateStatus("ready");
    }
  }, [videoRef, updateStatus]);

  // Đổi câu thì khung hình đổi theo: tua tới đầu câu khi video đang dừng. Video chưa có metadata
  // (vừa mở bài, vừa tải lại) thì đợi `loadedmetadata` rồi mới tua.
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    const seek = () => {
      showSentenceFrame(video, startSec);
    };
    if (video.readyState >= HTMLMediaElement.HAVE_METADATA) {
      seek();
      return;
    }
    video.addEventListener("loadedmetadata", seek, { once: true });
    return () => video.removeEventListener("loadedmetadata", seek);
  }, [startSec, nonce, videoRef]);

  // Đổi `src` đã tự nạp lại; `load()` để chắc chắn bỏ trạng thái lỗi cũ của phần tử.
  useEffect(() => {
    if (nonce !== null) videoRef.current?.load();
  }, [nonce, videoRef]);

  const reload = useMutation({
    mutationFn: () => reloadLessonVideo(lessonId),
    onSuccess: () => {
      updateStatus("loading");
      setNonce(Date.now());
    },
    onError: (error: Error) => {
      toast.error(error.message);
    },
  });

  const base = lessonVideoUrl(lessonId);
  const src = nonce === null ? base : `${base}?v=${nonce}`;

  return (
    <div className="relative aspect-video w-full shrink-0 bg-video">
      <video
        ref={videoRef}
        src={src}
        playsInline
        preload="auto"
        onCanPlay={() => updateStatus("ready")}
        onError={() => updateStatus("error")}
        className="absolute inset-0 size-full object-contain"
      />
      <div className="pointer-events-none absolute inset-x-0 bottom-0 flex items-end justify-between px-3 py-2.5 text-xs text-[color:var(--slate-8)]">
        <span className="font-mono">
          {formatClockTenths(startSec)} – {formatClockTenths(endSec)}
        </span>
        <span>Câu {sentenceNumber}</span>
      </div>
      {status === "loading" ? (
        <div
          role="status"
          className="absolute inset-0 flex items-center justify-center bg-video text-sm text-[color:var(--slate-8)]"
        >
          Đang tải video…
        </div>
      ) : null}
      {status === "error" ? (
        <div
          role="alert"
          className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-video px-6 text-center"
        >
          <p className="m-0 text-sm text-[color:var(--slate-4)]">
            Không phát được video của bài này.
          </p>
          <Button
            variant="outline"
            disabled={reload.isPending}
            onClick={() => reload.mutate()}
          >
            {reload.isPending ? "Đang tải lại…" : "Tải lại video"}
          </Button>
        </div>
      ) : null}
    </div>
  );
}

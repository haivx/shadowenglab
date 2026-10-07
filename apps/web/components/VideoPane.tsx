"use client";

import type { RefObject } from "react";
import { lessonVideoUrl } from "@/lib/api";

/** `mm:ss.s` cho lớp phủ khoảng thời gian của câu (UI-SPEC S3 Video). */
export function formatClockTenths(seconds: number): string {
  const tenths = Math.max(0, Math.floor(seconds * 10));
  const minutes = Math.floor(tenths / 600);
  const secs = Math.floor((tenths % 600) / 10);
  const tenth = tenths % 10;
  return `${String(minutes).padStart(2, "0")}:${String(secs).padStart(2, "0")}.${tenth}`;
}

interface VideoPaneProps {
  lessonId: string;
  /** PracticeRoom đọc phần tử này qua ref để phát đoạn câu mẫu. */
  videoRef: RefObject<HTMLVideoElement>;
  startSec: number;
  endSec: number;
  /** Số thứ tự câu hiển thị (bắt đầu từ 1). */
  sentenceNumber: number;
}

/** Video tự host 16:9, không điều khiển gốc (PLY-01, D-17). Không có YouTube IFrame. */
export function VideoPane({
  lessonId,
  videoRef,
  startSec,
  endSec,
  sentenceNumber,
}: VideoPaneProps) {
  return (
    <div className="relative aspect-video w-full shrink-0 bg-video">
      <video
        ref={videoRef}
        src={lessonVideoUrl(lessonId)}
        playsInline
        preload="auto"
        className="absolute inset-0 size-full object-contain"
      />
      <div className="pointer-events-none absolute inset-x-0 bottom-0 flex items-end justify-between px-3 py-2.5 text-xs text-[color:var(--slate-8)]">
        <span className="font-mono">
          {formatClockTenths(startSec)} – {formatClockTenths(endSec)}
        </span>
        <span>Câu {sentenceNumber}</span>
      </div>
    </div>
  );
}

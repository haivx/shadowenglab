"use client";

import type { VideoPreview } from "@shadowenglab/contracts";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { X } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { RangePicker } from "@/components/RangePicker";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiRequestError, createLesson, previewVideo } from "@/lib/api";
import { formatClock, safeThumbnailUrl } from "@/lib/lessonView";
import { queryKeys } from "@/lib/queries";
import {
  DEFAULT_RANGE_END_SEC,
  LONG_VIDEO_SEC,
  estimateMinutes,
  estimateSentences,
  type TimeRange,
} from "@/lib/time";

/** Chờ người dùng dán/gõ xong rồi mới hỏi backend (T-02-38). */
export const PREVIEW_DEBOUNCE_MS = 400;

const CHANNEL_URL_MESSAGE =
  "Đây là link kênh. Hãy dán link một video (có “watch?v=” hoặc “youtu.be/”).";
const INVALID_URL_MESSAGE =
  "Link này không phải link video YouTube. Hãy dán link có “watch?v=” hoặc “youtu.be/”.";
const VIDEO_UNAVAILABLE_MESSAGE =
  "Không lấy được video này (giới hạn khu vực, video riêng tư hoặc livestream). Thử video khác.";
const DUPLICATE_MESSAGE = "Video đã được tạo bài trước đó.";

/** Câu lỗi dưới ô link theo mã lỗi; mã khác dùng thông điệp tiếng Việt của backend. */
function previewErrorText(error: unknown): string {
  if (error instanceof ApiRequestError) {
    switch (error.error.code) {
      case "channel_url":
        return CHANNEL_URL_MESSAGE;
      case "invalid_url":
        return INVALID_URL_MESSAGE;
      case "video_unavailable":
      case "live_video":
        return VIDEO_UNAVAILABLE_MESSAGE;
      default:
        return error.error.message;
    }
  }
  return error instanceof Error ? error.message : "Không lấy được video này.";
}

/** Bỏ dấu chấm cuối để ghép vào `Không tạo được bài: {message}. Thử lại.` */
function withoutTrailingPeriod(message: string): string {
  return message.replace(/[.\s]+$/, "");
}

function PreviewSkeleton() {
  return (
    <div
      className="flex flex-col gap-2"
      aria-busy="true"
      data-testid="preview-skeleton"
    >
      <div className="flex gap-4 rounded-xl border border-border bg-[color:var(--slate-2)] p-3">
        <Skeleton className="aspect-video w-40 shrink-0 rounded" />
        <div className="flex min-w-0 flex-1 flex-col gap-1.5">
          <Skeleton className="h-4 w-4/5" />
          <Skeleton className="h-3.5 w-2/5" />
          <Skeleton className="h-3 w-3/5" />
        </div>
      </div>
      <p role="status" className="text-[13px] text-muted-foreground">
        Đang lấy thông tin video…
      </p>
    </div>
  );
}

function PreviewBlock({ preview }: { preview: VideoPreview }) {
  const thumbnail = safeThumbnailUrl(preview.thumbnailUrl);
  const meta = preview.channel
    ? `${formatClock(preview.durationSec)} · ${preview.channel}`
    : formatClock(preview.durationSec);
  return (
    <div className="flex gap-4 rounded-xl border border-border bg-[color:var(--slate-2)] p-3">
      <div className="aspect-video w-40 shrink-0 overflow-hidden rounded bg-video">
        {thumbnail ? (
          // Thẻ <img> thường (UI-SPEC): ảnh YouTube từ xa, tránh cấu hình next/image.
          <img
            src={thumbnail}
            alt=""
            loading="lazy"
            className="size-full object-cover"
          />
        ) : null}
      </div>
      <div className="flex min-w-0 flex-col gap-1.5">
        <span
          className="line-clamp-2 text-base font-bold leading-[1.3]"
          title={preview.title}
        >
          {preview.title}
        </span>
        <span className="text-sm text-muted-foreground">{meta}</span>
        <span className="text-[13px] text-muted-foreground">
          Giọng và chất lượng audio sẽ biết sau khi phân tích.
        </span>
      </div>
    </div>
  );
}

/** Quy tắc chọn video (Liam 2026-10-10), khớp hành vi thật: trần 6 phút (`MAX_RANGE_S`), chọn đoạn
 * cho video dài, nhãn "Có nhạc nền", lỗi `live_video` / `channel_url` / `video_unavailable`. */
const VIDEO_GUIDELINES = [
  "Dài tối đa 6 phút thì dùng cả video. Dài hơn: chọn một đoạn ≤ 6 phút sau khi dán link (tạo nhiều bài cho các đoạn khác nhau).",
  "Giọng Mỹ, nói rõ, tốt nhất 1–2 người, ít nói chồng lên nhau.",
  "Audio sạch: ít nhạc nền, vỗ tay, tiếng cười. Có nhạc nền vẫn tạo được, nhưng vài câu sẽ không chấm được.",
  "Video công khai; không dùng livestream, link kênh hay playlist.",
] as const;

function VideoGuidelines() {
  return (
    <section
      aria-labelledby="video-guidelines-title"
      className="flex flex-col gap-1.5 text-[13px] leading-[1.45] text-muted-foreground"
    >
      <h3
        id="video-guidelines-title"
        className="m-0 text-[13px] font-semibold text-foreground"
      >
        Video phù hợp
      </h3>
      <ul className="m-0 flex list-disc flex-col gap-1 pl-5">
        {VIDEO_GUIDELINES.map((rule) => (
          <li key={rule}>{rule}</li>
        ))}
      </ul>
    </section>
  );
}

/** Video ≤ 6 phút: dùng toàn bộ, không có thanh chọn đoạn (backend áp cùng quy tắc). */
function WholeVideoNote({ durationSec }: { durationSec: number }) {
  const [low, high] = estimateSentences(durationSec);
  return (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <p className="text-[13px] text-muted-foreground">
        Video ngắn hơn 6 phút nên dùng toàn bộ.
      </p>
      <div className="flex flex-col gap-0.5 text-[13px] text-muted-foreground">
        <span>
          ≈ {low}–{high} câu
        </span>
        <span>Xử lý ≈ {estimateMinutes(durationSec)} phút, chạy nền</span>
      </div>
    </div>
  );
}

function DuplicateNotice({ lessonId }: { lessonId: string }) {
  return (
    <div role="alert" className="flex flex-col gap-1 text-[13px]">
      <span className="text-destructive-text">{DUPLICATE_MESSAGE}</span>
      <Link
        href={`/lessons/${encodeURIComponent(lessonId)}`}
        className="text-sm font-semibold underline"
      >
        Mở bài đã có
      </Link>
    </div>
  );
}

export interface CreateLessonDialogProps {
  open: boolean;
  onClose: () => void;
}

/**
 * S2: dán link, xem preview hoặc lỗi chính xác, rồi `Tạo bài` (chạy nền, LES-03).
 * Backend là ranh giới tin cậy cho URL (T-02-37); client chỉ gửi qua `previewVideo`.
 */
export function CreateLessonDialog({ open, onClose }: CreateLessonDialogProps) {
  const queryClient = useQueryClient();
  const [input, setInput] = useState("");
  const [committed, setCommitted] = useState("");
  const [duplicateId, setDuplicateId] = useState<string | undefined>();
  const [range, setRange] = useState<TimeRange | null>(null);

  const trimmed = input.trim();

  useEffect(() => {
    const timer = setTimeout(() => setCommitted(trimmed), PREVIEW_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [trimmed]);

  const preview = useQuery({
    queryKey: ["videoPreview", committed],
    queryFn: () => previewVideo(committed),
    enabled: committed !== "",
    retry: false,
  });

  const settled = trimmed === committed;
  const waiting = trimmed !== "" && (!settled || preview.isFetching);
  const previewData = settled && !preview.isFetching ? preview.data : undefined;
  const previewError =
    settled && trimmed !== "" && !preview.isFetching && preview.isError
      ? previewErrorText(preview.error)
      : undefined;
  const longVideo =
    previewData !== undefined && previewData.durationSec > LONG_VIDEO_SEC;
  // Video dài: cần đoạn hợp lệ từ RangePicker. Video ngắn: không gửi đoạn.
  const rangeReady = !longVideo || range !== null;
  const sentRange = longVideo && range !== null ? range : undefined;
  // `existingLessonId` của backend chỉ tính cho đoạn mặc định (quy tắc trùng, 02-01).
  const isDefaultRange =
    sentRange === undefined ||
    (sentRange.start === 0 && sentRange.end === DEFAULT_RANGE_END_SEC);
  const existingId =
    duplicateId ??
    (previewData && isDefaultRange ? previewData.existingLessonId : undefined);

  const handleRangeChange = useCallback((next: TimeRange | null) => {
    setRange(next);
    setDuplicateId(undefined);
  }, []);

  const create = useMutation({
    mutationFn: () =>
      createLesson({
        url: committed,
        ...(sentRange ? { start: sentRange.start, end: sentRange.end } : {}),
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.lessons });
      onClose();
    },
    onError: (error: unknown) => {
      if (
        error instanceof ApiRequestError &&
        error.error.code === "duplicate_lesson" &&
        error.error.lessonId !== undefined
      ) {
        setDuplicateId(error.error.lessonId);
        return;
      }
      const message =
        error instanceof Error ? withoutTrailingPeriod(error.message) : "";
      toast.error(`Không tạo được bài: ${message}. Thử lại.`, {
        action: { label: "Thử lại", onClick: () => create.mutate() },
      });
    },
  });

  const canSubmit =
    previewData !== undefined &&
    rangeReady &&
    existingId === undefined &&
    !create.isPending;

  const showUrlError = previewError !== undefined;

  function handleChange(value: string) {
    setInput(value);
    setDuplicateId(undefined);
  }

  return (
    <Dialog open={open} onOpenChange={(next) => (next ? undefined : onClose())}>
      <DialogContent aria-describedby={undefined}>
        <DialogHeader className="items-center">
          <DialogTitle>Tạo bài từ YouTube</DialogTitle>
          <DialogClose asChild>
            <Button
              size="icon"
              variant="ghost"
              aria-label="Đóng"
              title="Đóng"
              className="text-muted-foreground"
            >
              <X aria-hidden="true" />
            </Button>
          </DialogClose>
        </DialogHeader>

        <form
          className="flex flex-col gap-6"
          onSubmit={(event) => {
            event.preventDefault();
            if (canSubmit) create.mutate();
          }}
        >
          <div className="flex flex-col gap-2">
            <Label htmlFor="yt-url">Link YouTube</Label>
            <Input
              id="yt-url"
              type="url"
              inputMode="url"
              autoComplete="off"
              spellCheck={false}
              placeholder="Dán link video YouTube"
              value={input}
              onChange={(event) => handleChange(event.target.value)}
              onBlur={() => setCommitted(trimmed)}
              aria-invalid={showUrlError || existingId !== undefined}
              aria-describedby={
                showUrlError || existingId !== undefined
                  ? "yt-url-error"
                  : undefined
              }
              className="h-12 px-3.5 text-[15px]"
            />
            <div id="yt-url-error">
              {showUrlError ? (
                <p role="alert" className="text-[13px] text-destructive-text">
                  {previewError}
                </p>
              ) : null}
              {existingId !== undefined ? (
                <DuplicateNotice lessonId={existingId} />
              ) : null}
            </div>
          </div>

          {!waiting && !previewData ? <VideoGuidelines /> : null}
          {waiting ? <PreviewSkeleton /> : null}
          {previewData ? <PreviewBlock preview={previewData} /> : null}
          {previewData && longVideo ? (
            <RangePicker
              key={previewData.videoId}
              durationSec={previewData.durationSec}
              onChange={handleRangeChange}
            />
          ) : null}
          {previewData && !longVideo ? (
            <WholeVideoNote durationSec={previewData.durationSec} />
          ) : null}

          <DialogFooter>
            <Button type="button" variant="outline" size="lg" onClick={onClose}>
              Huỷ
            </Button>
            <Button type="submit" size="lg" disabled={!canSubmit}>
              {create.isPending ? "Đang tạo…" : "Tạo bài"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

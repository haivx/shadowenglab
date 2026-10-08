"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";
import type { Segment } from "@shadowenglab/contracts";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { translateSegment, updateSegmentText } from "@/lib/api";
import { releaseFocusOnPointerUp } from "@/lib/player/useShortcuts";
import { patchLessonSegment } from "@/lib/segmentCache";
import { cn } from "@/lib/utils";

/** `mm:ss` của thời điểm bắt đầu câu. */
function formatMmSs(seconds: number): string {
  const whole = Math.max(0, Math.floor(seconds));
  const minutes = Math.floor(whole / 60);
  return `${String(minutes).padStart(2, "0")}:${String(whole % 60).padStart(2, "0")}`;
}

const GROUP_LABEL_CLASS =
  "text-xs font-bold uppercase tracking-[0.06em] text-[color:var(--slate-9)]";

const TRANSLATING_TEXT = "Đang dịch…";
const TRANSLATE_FAILED_TEXT = "Không dịch được câu này. Bấm Dịch để thử lại.";
const NEEDS_KEY_TEXT = "Cần OPENAI_API_KEY";
const SAVE_FAILED_TEXT = "Không lưu được. Thử lại.";
const MAX_SEGMENT_TEXT = 500;

export type TranslationRowStatus = "idle" | "loading" | "failed";

/** Trạng thái bản dịch cho TranscriptList; `toggle` dùng chung cho nút `Dịch` và phím T. */
export interface TranslationTool {
  on: boolean;
  /** Không có key và câu hiện tại chưa có bản dịch lưu sẵn: nút khoá (D-16). */
  blocked: boolean;
  toggle: () => void;
  statusOf: (segmentIndex: number) => TranslationRowStatus;
}

interface UseTranslationToolOptions {
  lessonId: string;
  /** Câu đang tập. */
  segment: Segment | undefined;
  hasKey: boolean;
}

/**
 * Bật tắt dòng dịch (D-16). Khi bật, câu hiện tại chưa có bản dịch sẽ được dịch đúng một lần
 * (POST …/translate), kết quả ghi vào cache của bài; bản dịch đã lưu hiện được cả khi không có key.
 * Một câu chỉ có một yêu cầu đang chạy; lỗi thì chờ người dùng bấm `Dịch` để thử lại.
 */
export function useTranslationTool({
  lessonId,
  segment,
  hasKey,
}: UseTranslationToolOptions): TranslationTool {
  const queryClient = useQueryClient();
  const [on, setOn] = useState(false);
  const [failedIndex, setFailedIndex] = useState<number | null>(null);
  const [pending, setPending] = useState<ReadonlySet<number>>(new Set());
  const inFlight = useRef(new Set<number>());

  const { mutate } = useMutation({
    mutationFn: (segmentIndex: number) =>
      translateSegment(lessonId, segmentIndex),
    onSuccess: (updated) => patchLessonSegment(queryClient, lessonId, updated),
    onError: (_error, segmentIndex) => setFailedIndex(segmentIndex),
    onSettled: (_data, _error, segmentIndex) => {
      inFlight.current.delete(segmentIndex);
      setPending((prev) => {
        const next = new Set(prev);
        next.delete(segmentIndex);
        return next;
      });
    },
  });

  const segmentIndex = segment?.index;
  const hasTranslation = Boolean(segment?.translation);
  const blocked = !hasKey && !hasTranslation;

  useEffect(() => {
    if (!on || segmentIndex === undefined || hasTranslation || !hasKey) return;
    if (failedIndex === segmentIndex || inFlight.current.has(segmentIndex)) {
      return;
    }
    inFlight.current.add(segmentIndex);
    setPending((prev) => new Set(prev).add(segmentIndex));
    mutate(segmentIndex);
  }, [on, segmentIndex, hasTranslation, hasKey, failedIndex, mutate]);

  const toggle = useCallback(() => {
    if (on && segmentIndex !== undefined && failedIndex === segmentIndex) {
      setFailedIndex(null); // thử lại
      return;
    }
    if (!on && blocked) return;
    if (!on) setFailedIndex(null);
    setOn((prev) => !prev);
  }, [on, blocked, segmentIndex, failedIndex]);

  const statusOf = useCallback(
    (index: number): TranslationRowStatus => {
      if (pending.has(index)) return "loading";
      if (failedIndex === index) return "failed";
      return "idle";
    },
    [pending, failedIndex],
  );

  return { on, blocked: blocked && !on, toggle, statusOf };
}

interface TranscriptListProps {
  segments: readonly Segment[];
  /** Chỉ số (từ 0) của câu đang tập. */
  currentIndex: number;
  /** Câu đã tập (voicedAttempts >= 1, D-08): chấm xám trung tính. */
  practiced: ReadonlySet<number>;
  /** Chọn câu: dừng phát và đưa câu đó thành câu hiện tại. */
  onSelect: (index: number) => void;
  lessonId: string;
  /** Bản dịch theo câu (nút `Dịch`, phím T). */
  translation: TranslationTool;
  /** Chỉ cho sửa câu khi machine ở idle / reviewing / noVoice / error. */
  canEdit: boolean;
}

/** Danh sách câu của S3, cuộn bên trong aside; hàng hiện tại tự cuộn vào khung nhìn. */
export function TranscriptList({
  segments,
  currentIndex,
  practiced,
  onSelect,
  lessonId,
  translation,
  canEdit,
}: TranscriptListProps) {
  const queryClient = useQueryClient();
  const currentRef = useRef<HTMLButtonElement>(null);
  // Input không forwardRef (React 18): lấy ô nhập qua form.
  const formRef = useRef<HTMLFormElement>(null);
  const current = segments[currentIndex];

  // Sửa câu (PLY-04, G14): chỉ câu hiện tại, chỉ khi machine cho phép.
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [draft, setDraft] = useState("");
  const [saveFailed, setSaveFailed] = useState(false);
  const isEditing = editingIndex === currentIndex && canEdit;

  const save = useMutation({
    mutationFn: (input: { segmentIndex: number; text: string }) =>
      updateSegmentText(lessonId, input.segmentIndex, input.text),
    onSuccess: (updated) => {
      patchLessonSegment(queryClient, lessonId, updated);
      setEditingIndex(null);
      setSaveFailed(false);
    },
    onError: () => setSaveFailed(true),
  });

  // Rời câu đang sửa hoặc machine không còn cho sửa: thoát chế độ sửa.
  useEffect(() => {
    if (editingIndex !== null && (editingIndex !== currentIndex || !canEdit)) {
      setEditingIndex(null);
    }
  }, [editingIndex, currentIndex, canEdit]);

  useEffect(() => {
    if (isEditing) formRef.current?.querySelector("input")?.focus();
  }, [isEditing]);

  const startEdit = () => {
    if (!canEdit || !current) return;
    setDraft(current.text);
    setSaveFailed(false);
    setEditingIndex(currentIndex);
  };
  const cancelEdit = () => {
    setEditingIndex(null);
    setSaveFailed(false);
  };
  const submitEdit = () => {
    if (!current || save.isPending) return;
    const text = draft.trim();
    if (text === "") return;
    if (text === current.text) {
      cancelEdit();
      return;
    }
    save.mutate({ segmentIndex: current.index, text });
  };

  useEffect(() => {
    currentRef.current?.scrollIntoView({ block: "nearest", behavior: "auto" });
  }, [currentIndex]);

  return (
    <section
      aria-label="Transcript"
      className="flex max-h-[360px] min-h-0 flex-1 flex-col min-[1160px]:max-h-none"
    >
      <div className="flex min-h-11 items-center justify-between px-4 pt-2.5">
        <span className={GROUP_LABEL_CLASS}>
          Transcript · {segments.length} câu
        </span>
        <span className="flex gap-1">
          <Tooltip>
            {/* Button không forwardRef (React 18): span làm trigger, focus của nút nổi lên span. */}
            <TooltipTrigger asChild>
              <span className="inline-flex">
                <Button
                  variant="ghost"
                  kbd="T"
                  aria-pressed={translation.on}
                  aria-disabled={translation.blocked ? "true" : undefined}
                  onPointerUp={
                    translation.blocked ? undefined : releaseFocusOnPointerUp
                  }
                  onClick={translation.toggle}
                  className={cn(
                    "px-3 text-[13px] aria-pressed:bg-[color:var(--slate-4)]",
                    translation.blocked && "cursor-not-allowed opacity-50",
                  )}
                >
                  Dịch
                </Button>
              </span>
            </TooltipTrigger>
            {translation.blocked ? (
              <TooltipContent>{NEEDS_KEY_TEXT}</TooltipContent>
            ) : null}
          </Tooltip>
          <Button
            variant="ghost"
            aria-pressed={isEditing}
            aria-disabled={canEdit ? undefined : "true"}
            onPointerUp={canEdit ? releaseFocusOnPointerUp : undefined}
            onClick={isEditing ? cancelEdit : startEdit}
            className={cn(
              "px-3 text-[13px] aria-pressed:bg-[color:var(--slate-4)]",
              !canEdit && "cursor-not-allowed opacity-50",
            )}
          >
            Sửa câu
          </Button>
        </span>
      </div>
      <span role="status" className="sr-only">
        {translation.on && current
          ? currentStatusText(current, translation.statusOf(current.index))
          : ""}
      </span>
      <ol className="m-0 flex min-h-0 flex-1 list-none flex-col overflow-y-auto p-0 py-2">
        {segments.map((segment, index) => {
          const isCurrent = index === currentIndex;
          const isPracticed = practiced.has(index);
          if (isCurrent && isEditing) {
            return (
              <li key={segment.index}>
                <form
                  ref={formRef}
                  aria-label="Sửa câu"
                  onSubmit={(event) => {
                    event.preventDefault();
                    submitEdit();
                  }}
                  className="grid w-full grid-cols-[44px_minmax(0,1fr)] gap-2 border-l-[3px] border-foreground bg-card py-2.5 pl-[13px] pr-4 text-sm shadow-[inset_0_1px_0_var(--border),inset_0_-1px_0_var(--border)]"
                >
                  <span className="pt-3 font-mono text-[11px] font-normal text-foreground">
                    {formatMmSs(segment.start)}
                  </span>
                  <div className="flex min-w-0 flex-col gap-2">
                    <Input
                      aria-label="Nội dung câu"
                      maxLength={MAX_SEGMENT_TEXT}
                      value={draft}
                      aria-invalid={saveFailed ? true : undefined}
                      onChange={(event) => setDraft(event.target.value)}
                      onKeyDown={(event) => {
                        if (event.key === "Escape") {
                          event.preventDefault();
                          cancelEdit();
                        }
                      }}
                    />
                    {saveFailed ? (
                      <p
                        role="alert"
                        className="m-0 text-[13px] font-normal text-destructive"
                      >
                        {SAVE_FAILED_TEXT}
                      </p>
                    ) : null}
                    <div className="flex gap-2">
                      <Button
                        type="submit"
                        variant="solid"
                        disabled={save.isPending || draft.trim() === ""}
                      >
                        Lưu
                      </Button>
                      <Button
                        type="button"
                        variant="ghost"
                        disabled={save.isPending}
                        onClick={cancelEdit}
                      >
                        Huỷ
                      </Button>
                    </div>
                  </div>
                </form>
              </li>
            );
          }
          return (
            <li key={segment.index}>
              <button
                type="button"
                ref={isCurrent ? currentRef : undefined}
                aria-current={isCurrent ? "true" : undefined}
                onPointerUp={releaseFocusOnPointerUp}
                onClick={() => onSelect(index)}
                className={cn(
                  "grid min-h-11 w-full grid-cols-[44px_minmax(0,1fr)_28px] gap-2 text-left text-sm leading-[1.45] transition-colors [transition-duration:120ms]",
                  isCurrent
                    ? "border-l-[3px] border-foreground bg-card py-2.5 pl-[13px] pr-4 font-semibold text-foreground shadow-[inset_0_1px_0_var(--border),inset_0_-1px_0_var(--border)]"
                    : cn(
                        "px-4 py-2 hover:bg-muted",
                        isPracticed
                          ? "text-muted-foreground"
                          : "text-foreground",
                      ),
                )}
              >
                <span
                  className={cn(
                    "pt-[3px] font-mono text-[11px] font-normal",
                    isCurrent
                      ? "text-foreground"
                      : !isPracticed && "text-[color:var(--slate-9)]",
                  )}
                >
                  {formatMmSs(segment.start)}
                </span>
                <span className="flex min-w-0 flex-col gap-0.5">
                  <span>{segment.text}</span>
                  {translation.on ? (
                    <TranslationLine
                      segment={segment}
                      isCurrent={isCurrent}
                      status={translation.statusOf(segment.index)}
                    />
                  ) : null}
                </span>
                <span className="flex justify-end pt-1.5">
                  {isPracticed ? (
                    <>
                      <span
                        aria-hidden="true"
                        className="size-2 rounded-full bg-muted-foreground"
                      />
                      <span className="sr-only">Đã tập</span>
                    </>
                  ) : null}
                </span>
              </button>
            </li>
          );
        })}
      </ol>
    </section>
  );
}

function currentStatusText(
  segment: Segment,
  status: TranslationRowStatus,
): string {
  if (segment.translation) return "";
  if (status === "loading") return TRANSLATING_TEXT;
  if (status === "failed") return TRANSLATE_FAILED_TEXT;
  return "";
}

/** Dòng dịch 13px dưới chữ của hàng (UI-SPEC E8 partial, E12). Chỉ hàng hiện tại hiện đang dịch / lỗi. */
function TranslationLine({
  segment,
  isCurrent,
  status,
}: {
  segment: Segment;
  isCurrent: boolean;
  status: TranslationRowStatus;
}) {
  const text = segment.translation
    ? segment.translation
    : isCurrent
      ? currentStatusText(segment, status)
      : "";
  if (!text) return null;
  return (
    <span className="break-words text-[13px] font-normal leading-[1.4] text-muted-foreground">
      {text}
    </span>
  );
}

/** Hàng khung xương trong lúc bài đang tải (UI-SPEC E8 loading). */
export function TranscriptListSkeleton() {
  return (
    <section
      aria-label="Transcript"
      aria-busy="true"
      className="flex min-h-0 flex-1 flex-col"
    >
      <div className="flex min-h-11 items-center px-4 pt-2.5">
        <Skeleton className="h-3 w-32" />
      </div>
      <div className="flex flex-col gap-3 px-4 py-3">
        {Array.from({ length: 8 }, (_, index) => (
          <div key={index} className="flex items-center gap-2">
            <Skeleton className="h-3 w-11" />
            <Skeleton className="h-4 flex-1" />
          </div>
        ))}
      </div>
    </section>
  );
}

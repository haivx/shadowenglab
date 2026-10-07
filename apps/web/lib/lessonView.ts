import type {
  LessonError,
  LessonListItem,
  LessonStatus,
} from "@shadowenglab/contracts";

/**
 * Hàm thuần cho S1 Thư viện: chuẩn bị dữ liệu hiển thị từ `LessonListItem`.
 * Không có điểm số ở P1 (D-08): chỉ đếm câu đã tập.
 */

/** Năm bước xử lý, theo thứ tự chạy (UI-SPEC "S1 — library, cards, job steps"). */
export const STEP_ORDER = [
  "downloading",
  "separating",
  "transcribing",
  "segmenting",
  "analyzing",
] as const;

export type JobStep = (typeof STEP_ORDER)[number];

export const STEP_LABELS: Record<JobStep, string> = {
  downloading: "Tải video",
  separating: "Tách giọng",
  transcribing: "Phiên âm",
  segmenting: "Chia câu",
  analyzing: "Phân tích bản gốc",
};

/** Tiền tố lỗi theo bước (UI-SPEC "Failed prefixes by step"). */
const FAILED_PREFIXES: Record<JobStep, string> = {
  downloading: "Không tải được video",
  separating: "Không tách được giọng",
  transcribing: "Không phiên âm được",
  segmenting: "Không chia được câu",
  analyzing: "Không phân tích được bản gốc",
};

const FALLBACK_FAILED_PREFIX = "Không xử lý được bài";
const FALLBACK_STEP_LABEL = "xử lý";
const INTERRUPTED_MESSAGE = "bị gián đoạn";

export type StepState = "done" | "running" | "pending";

export interface StepRow {
  step: JobStep;
  label: string;
  state: StepState;
}

function isJobStep(value: string): value is JobStep {
  return (STEP_ORDER as readonly string[]).includes(value);
}

/**
 * Năm dòng bước theo trạng thái job. `queued` (và `failed`, không biết bước
 * nào) = tất cả chờ; `ready` = tất cả xong.
 */
export function stepRows(status: LessonStatus): StepRow[] {
  const runningIndex = isJobStep(status) ? STEP_ORDER.indexOf(status) : -1;
  return STEP_ORDER.map((step, index): StepRow => {
    let state: StepState = "pending";
    if (status === "ready") state = "done";
    else if (runningIndex >= 0 && index < runningIndex) state = "done";
    else if (index === runningIndex) state = "running";
    return { step, label: STEP_LABELS[step], state };
  });
}

function stripTrailingPeriod(text: string): string {
  return text.replace(/[.\s]+$/u, "");
}

/** Câu lỗi của thẻ failed (D-03 cho trường hợp bị gián đoạn). */
export function failureText(error: LessonError | undefined): string {
  const step = error?.step ?? "";
  const message = (error?.message ?? "").trim();
  if (stripTrailingPeriod(message).toLowerCase() === INTERRUPTED_MESSAGE) {
    const label = isJobStep(step)
      ? STEP_LABELS[step].toLowerCase()
      : FALLBACK_STEP_LABEL;
    return `Bị gián đoạn ở bước ${label}. Bấm Thử lại để chạy lại.`;
  }
  const prefix = isJobStep(step)
    ? FAILED_PREFIXES[step]
    : FALLBACK_FAILED_PREFIX;
  const body = stripTrailingPeriod(message);
  return body ? `${prefix}: ${body}.` : `${prefix}.`;
}

export function isProcessing(status: LessonStatus): boolean {
  return status !== "ready" && status !== "failed";
}

/** `{n} bài · {n} sẵn sàng · {n} đang xử lý · {n} lỗi`, bỏ đoạn có số 0. */
export function librarySummary(items: readonly LessonListItem[]): string {
  if (items.length === 0) return "";
  let ready = 0;
  let processing = 0;
  let failed = 0;
  for (const { lesson } of items) {
    if (lesson.status === "ready") ready += 1;
    else if (lesson.status === "failed") failed += 1;
    else processing += 1;
  }
  const parts = [`${items.length} bài`];
  if (ready > 0) parts.push(`${ready} sẵn sàng`);
  if (processing > 0) parts.push(`${processing} đang xử lý`);
  if (failed > 0) parts.push(`${failed} lỗi`);
  return parts.join(" · ");
}

export type LibraryTab = "all" | "practicing" | "done";

function allPracticed(item: LessonListItem): boolean {
  return item.segmentCount > 0 && item.firstUnpracticedIndex === null;
}

/**
 * `Đang tập` = ready, đã tập ≥ 1 câu và chưa hết; `Đã xong` = ready, mọi câu
 * đã tập. Bài đang xử lý hoặc lỗi chỉ hiện ở `Tất cả`.
 */
export function filterByTab(
  items: readonly LessonListItem[],
  tab: LibraryTab,
): LessonListItem[] {
  if (tab === "all") return [...items];
  return items.filter((item) => {
    if (item.lesson.status !== "ready") return false;
    if (tab === "done") return allPracticed(item);
    return item.practicedCount >= 1 && !allPracticed(item);
  });
}

export interface CardCta {
  label: string;
  variant: "solid" | "outline";
}

export function cardCta(item: LessonListItem): CardCta {
  if (allPracticed(item)) {
    return { label: "Tập lại từ đầu", variant: "outline" };
  }
  if (item.practicedCount === 0 || item.firstUnpracticedIndex === null) {
    return { label: "Bắt đầu tập", variant: "outline" };
  }
  return {
    label: `Tiếp tục ở câu ${item.firstUnpracticedIndex + 1}`,
    variant: "solid",
  };
}

/** `m:ss` (giây làm tròn xuống, phút không đệm số 0). */
export function formatClock(seconds: number): string {
  const total = Math.max(0, Math.floor(Number.isFinite(seconds) ? seconds : 0));
  const minutes = Math.floor(total / 60);
  const rest = total % 60;
  return `${minutes}:${String(rest).padStart(2, "0")}`;
}

/** Chỉ ảnh `https://` mới được dựng `<img>` (T-02-21). */
export function safeThumbnailUrl(url: string | undefined): string | undefined {
  return url !== undefined && url.startsWith("https://") ? url : undefined;
}

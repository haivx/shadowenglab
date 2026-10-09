import { keepPreviousData, useQuery } from "@tanstack/react-query";
import type { LessonListItem, SystemStatus } from "@shadowenglab/contracts";
import {
  getAttemptResult,
  getLesson,
  getLessonProgress,
  listAttempts,
  getSettings,
  getSystemStatus,
  listLessons,
} from "./api";

/** Chu kỳ poll khi còn bài đang xử lý hoặc model đang nạp (quyền chọn của planner). */
export const POLL_INTERVAL_MS = 2000;

export const queryKeys = {
  lessons: ["lessons"] as const,
  lesson: (id: string) => ["lessons", id] as const,
  lessonProgress: (id: string) => ["lessons", id, "progress"] as const,
  attempts: (id: string, index: number) =>
    ["lessons", id, "segments", index, "attempts"] as const,
  attemptResult: (id: string, index: number, attempt: number) =>
    ["lessons", id, "segments", index, "attempts", attempt] as const,
  systemStatus: ["system", "status"] as const,
  settings: ["settings"] as const,
};

/** Còn bài chưa ready/failed thì tiếp tục poll. */
export function lessonsPollInterval(
  items: LessonListItem[] | undefined,
): number | false {
  const busy = items?.some(
    (item) => item.lesson.status !== "ready" && item.lesson.status !== "failed",
  );
  return busy ? POLL_INTERVAL_MS : false;
}

export function useLessons() {
  return useQuery({
    queryKey: queryKeys.lessons,
    queryFn: listLessons,
    refetchInterval: (query) => lessonsPollInterval(query.state.data),
    placeholderData: keepPreviousData,
  });
}

export function useLesson(id: string) {
  return useQuery({
    queryKey: queryKeys.lesson(id),
    queryFn: () => getLesson(id),
  });
}

export function useLessonProgress(id: string) {
  return useQuery({
    queryKey: queryKeys.lessonProgress(id),
    queryFn: () => getLessonProgress(id),
  });
}

/** Danh sách lượt đã chấm của một câu; chỉ là phần bổ sung cho chip nên lỗi không chặn gì. */
export function useAttempts(lessonId: string, index: number) {
  return useQuery({
    queryKey: queryKeys.attempts(lessonId, index),
    queryFn: () => listAttempts(lessonId, index),
  });
}

/** Kết quả đã lưu của một lượt cũ; một kết quả đã lưu không bao giờ đổi nên không refetch. */
export function useAttemptResult(
  lessonId: string,
  index: number,
  attempt: number,
  enabled: boolean,
) {
  return useQuery({
    queryKey: queryKeys.attemptResult(lessonId, index, attempt),
    queryFn: () => getAttemptResult(lessonId, index, attempt),
    enabled,
    staleTime: Infinity,
  });
}

function modelsLoading(status: SystemStatus | undefined): boolean {
  if (!status) return false;
  return Object.values(status.models).some((state) => state === "loading");
}

export function useSystemStatus() {
  return useQuery({
    queryKey: queryKeys.systemStatus,
    queryFn: getSystemStatus,
    refetchInterval: (query) =>
      modelsLoading(query.state.data) ? POLL_INTERVAL_MS : false,
  });
}

export function useSettings() {
  return useQuery({
    queryKey: queryKeys.settings,
    queryFn: getSettings,
  });
}

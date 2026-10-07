import { keepPreviousData, useQuery } from "@tanstack/react-query";
import type { LessonListItem, SystemStatus } from "@shadowenglab/contracts";
import {
  getLesson,
  getLessonProgress,
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

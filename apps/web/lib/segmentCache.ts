import type { QueryClient } from "@tanstack/react-query";
import type { Lesson, Segment } from "@shadowenglab/contracts";
import { queryKeys } from "./queries";

/** Thay một câu (theo `index`) bằng bản server trả về; các câu khác giữ nguyên tham chiếu. */
export function replaceSegment(lesson: Lesson, updated: Segment): Lesson {
  return {
    ...lesson,
    segments: lesson.segments.map((segment) =>
      segment.index === updated.index ? updated : segment,
    ),
  };
}

/**
 * Ghi Segment server trả về (dịch, sửa câu, nới câu) vào cache của bài.
 * Cache chưa có thì bỏ qua: lần tải sau sẽ lấy bản đúng từ server.
 */
export function patchLessonSegment(
  queryClient: QueryClient,
  lessonId: string,
  updated: Segment,
): void {
  queryClient.setQueryData<Lesson>(queryKeys.lesson(lessonId), (lesson) =>
    lesson ? replaceSegment(lesson, updated) : lesson,
  );
}

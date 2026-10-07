import type { LessonListItem, LessonStatus } from "@shadowenglab/contracts";
import { describe, expect, it } from "vitest";
import {
  cardCta,
  failureText,
  filterByTab,
  formatClock,
  librarySummary,
  safeThumbnailUrl,
  stepRows,
} from "./lessonView";

interface ItemOptions {
  id?: string;
  status?: LessonStatus;
  segmentCount?: number;
  practicedCount?: number;
  firstUnpracticedIndex?: number | null;
}

function makeItem(options: ItemOptions = {}): LessonListItem {
  const segmentCount = options.segmentCount ?? 10;
  const practicedCount = options.practicedCount ?? 0;
  return {
    lesson: {
      id: options.id ?? "01HX",
      videoId: "abc123",
      title: "Một bài học",
      durationSec: 300,
      range: { start: 0, end: 300 },
      padMs: 150,
      status: options.status ?? "ready",
      createdAt: "2026-10-07T00:00:00Z",
    },
    segmentCount,
    practicedCount,
    firstUnpracticedIndex:
      options.firstUnpracticedIndex === undefined
        ? practicedCount >= segmentCount
          ? null
          : practicedCount
        : options.firstUnpracticedIndex,
  };
}

describe("stepRows", () => {
  it("trả đúng năm bước theo thứ tự với nhãn tiếng Việt", () => {
    expect(stepRows("queued").map((row) => row.label)).toEqual([
      "Tải video",
      "Tách giọng",
      "Phiên âm",
      "Chia câu",
      "Phân tích bản gốc",
    ]);
  });

  it("queued: tất cả đang chờ", () => {
    expect(stepRows("queued").every((row) => row.state === "pending")).toBe(
      true,
    );
  });

  it("bước giữa chừng: trước = xong, hiện tại = đang chạy, sau = chờ", () => {
    expect(stepRows("transcribing").map((row) => row.state)).toEqual([
      "done",
      "done",
      "running",
      "pending",
      "pending",
    ]);
  });

  it("bước đầu và bước cuối", () => {
    expect(stepRows("downloading")[0]?.state).toBe("running");
    expect(stepRows("analyzing").map((row) => row.state)).toEqual([
      "done",
      "done",
      "done",
      "done",
      "running",
    ]);
  });

  it("ready: tất cả xong", () => {
    expect(stepRows("ready").every((row) => row.state === "done")).toBe(true);
  });
});

describe("failureText", () => {
  it("ghép tiền tố bước và thông điệp, kết thúc bằng một dấu chấm", () => {
    expect(
      failureText({
        step: "downloading",
        message: "video bị giới hạn khu vực hoặc tắt tải xuống",
      }),
    ).toBe(
      "Không tải được video: video bị giới hạn khu vực hoặc tắt tải xuống.",
    );
  });

  it("không nhân đôi dấu chấm khi thông điệp đã có", () => {
    expect(failureText({ step: "separating", message: "hết bộ nhớ." })).toBe(
      "Không tách được giọng: hết bộ nhớ.",
    );
  });

  it("dùng đúng tiền tố cho từng bước", () => {
    expect(failureText({ step: "transcribing", message: "x" })).toBe(
      "Không phiên âm được: x.",
    );
    expect(failureText({ step: "analyzing", message: "x" })).toBe(
      "Không phân tích được bản gốc: x.",
    );
  });

  it("E3 partial: không có câu nói ở bước segmenting", () => {
    expect(
      failureText({
        step: "segmenting",
        message:
          "không tìm thấy câu nói nào trong đoạn này. Hãy chọn đoạn khác hoặc video khác.",
      }),
    ).toBe(
      "Không chia được câu: không tìm thấy câu nói nào trong đoạn này. Hãy chọn đoạn khác hoặc video khác.",
    );
  });

  it("bị gián đoạn: câu riêng nêu tên bước", () => {
    expect(failureText({ step: "separating", message: "bị gián đoạn" })).toBe(
      "Bị gián đoạn ở bước tách giọng. Bấm Thử lại để chạy lại.",
    );
  });

  it("bị gián đoạn không phân biệt hoa thường và dấu chấm cuối", () => {
    expect(failureText({ step: "downloading", message: "Bị gián đoạn." })).toBe(
      "Bị gián đoạn ở bước tải video. Bấm Thử lại để chạy lại.",
    );
  });

  it("bước ngoài năm bước (queued) dùng tiền tố dự phòng", () => {
    expect(failureText({ step: "queued", message: "lỗi lạ" })).toBe(
      "Không xử lý được bài: lỗi lạ.",
    );
  });

  it("thiếu error vẫn trả câu hợp lệ", () => {
    expect(failureText(undefined)).toBe("Không xử lý được bài.");
  });
});

describe("librarySummary", () => {
  it("rỗng khi chưa có bài", () => {
    expect(librarySummary([])).toBe("");
  });

  it("bỏ đoạn có số 0", () => {
    expect(librarySummary([makeItem({ status: "downloading" })])).toBe(
      "1 bài · 1 đang xử lý",
    );
    expect(librarySummary([makeItem()])).toBe("1 bài · 1 sẵn sàng");
  });

  it("đủ bốn đoạn", () => {
    expect(
      librarySummary([
        makeItem({ id: "a" }),
        makeItem({ id: "b", status: "queued" }),
        makeItem({ id: "c", status: "segmenting" }),
        makeItem({ id: "d", status: "failed" }),
      ]),
    ).toBe("4 bài · 1 sẵn sàng · 2 đang xử lý · 1 lỗi");
  });
});

describe("filterByTab", () => {
  const notStarted = makeItem({ id: "n", practicedCount: 0 });
  const practicing = makeItem({ id: "p", practicedCount: 3 });
  const done = makeItem({ id: "d", practicedCount: 10 });
  const processing = makeItem({ id: "q", status: "queued" });
  const failed = makeItem({ id: "f", status: "failed" });
  const all = [notStarted, practicing, done, processing, failed];

  it("all giữ mọi bài, kể cả đang xử lý và lỗi", () => {
    expect(filterByTab(all, "all").map((i) => i.lesson.id)).toEqual([
      "n",
      "p",
      "d",
      "q",
      "f",
    ]);
  });

  it("practicing chỉ có bài ready đã tập một phần", () => {
    expect(filterByTab(all, "practicing").map((i) => i.lesson.id)).toEqual([
      "p",
    ]);
  });

  it("done chỉ có bài ready đã tập hết", () => {
    expect(filterByTab(all, "done").map((i) => i.lesson.id)).toEqual(["d"]);
  });

  it("không có bài ready: hai tab lọc đều rỗng", () => {
    const none = [processing, failed];
    expect(filterByTab(none, "practicing")).toEqual([]);
    expect(filterByTab(none, "done")).toEqual([]);
    expect(filterByTab(none, "all")).toHaveLength(2);
  });

  it("mọi bài đã tập hết: practicing rỗng, done đủ", () => {
    const every = [
      done,
      makeItem({ id: "d2", practicedCount: 4, segmentCount: 4 }),
    ];
    expect(filterByTab(every, "practicing")).toEqual([]);
    expect(filterByTab(every, "done")).toHaveLength(2);
  });

  it("bài lỗi chỉ xuất hiện ở Tất cả dù đã có lượt tập", () => {
    const failedWithProgress = makeItem({
      id: "fp",
      status: "failed",
      practicedCount: 2,
    });
    expect(filterByTab([failedWithProgress], "practicing")).toEqual([]);
    expect(filterByTab([failedWithProgress], "done")).toEqual([]);
    expect(filterByTab([failedWithProgress], "all")).toHaveLength(1);
  });

  it("bài ready không có câu nào không bị tính là đã xong", () => {
    const empty = makeItem({ segmentCount: 0, practicedCount: 0 });
    expect(filterByTab([empty], "done")).toEqual([]);
    expect(filterByTab([empty], "practicing")).toEqual([]);
  });

  it("không đổi mảng đầu vào", () => {
    const input = [practicing, done];
    filterByTab(input, "done");
    expect(input).toHaveLength(2);
  });
});

describe("cardCta", () => {
  it("chưa tập câu nào: Bắt đầu tập, viền", () => {
    expect(cardCta(makeItem({ practicedCount: 0 }))).toEqual({
      label: "Bắt đầu tập",
      variant: "outline",
    });
  });

  it("đang tập: Tiếp tục ở câu i (đánh số từ 1), nút đặc", () => {
    expect(
      cardCta(makeItem({ practicedCount: 3, firstUnpracticedIndex: 3 })),
    ).toEqual({ label: "Tiếp tục ở câu 4", variant: "solid" });
  });

  it("tập chưa liên tục: lấy câu đầu tiên chưa tập", () => {
    expect(
      cardCta(makeItem({ practicedCount: 4, firstUnpracticedIndex: 1 })),
    ).toEqual({ label: "Tiếp tục ở câu 2", variant: "solid" });
  });

  it("đã tập hết: Tập lại từ đầu, viền", () => {
    expect(cardCta(makeItem({ practicedCount: 10 }))).toEqual({
      label: "Tập lại từ đầu",
      variant: "outline",
    });
  });

  it("không có câu nào: quay về Bắt đầu tập", () => {
    expect(
      cardCta(
        makeItem({
          segmentCount: 0,
          practicedCount: 0,
          firstUnpracticedIndex: null,
        }),
      ),
    ).toEqual({ label: "Bắt đầu tập", variant: "outline" });
  });
});

describe("formatClock", () => {
  it("định dạng m:ss", () => {
    expect(formatClock(0)).toBe("0:00");
    expect(formatClock(5)).toBe("0:05");
    expect(formatClock(65)).toBe("1:05");
    expect(formatClock(300)).toBe("5:00");
    expect(formatClock(754)).toBe("12:34");
  });

  it("làm tròn xuống và chặn giá trị xấu", () => {
    expect(formatClock(59.9)).toBe("0:59");
    expect(formatClock(-3)).toBe("0:00");
    expect(formatClock(Number.NaN)).toBe("0:00");
  });
});

describe("safeThumbnailUrl", () => {
  it("chỉ nhận https", () => {
    expect(safeThumbnailUrl("https://i.ytimg.com/vi/x/hq.jpg")).toBe(
      "https://i.ytimg.com/vi/x/hq.jpg",
    );
    expect(safeThumbnailUrl("http://i.ytimg.com/x.jpg")).toBeUndefined();
    expect(safeThumbnailUrl("javascript:alert(1)")).toBeUndefined();
    expect(safeThumbnailUrl(undefined)).toBeUndefined();
  });
});

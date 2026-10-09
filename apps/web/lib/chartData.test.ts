import { describe, expect, it } from "vitest";
import type { Issue } from "@shadowenglab/contracts";
import {
  buildChartRows,
  chartAriaLabel,
  chartDrawable,
  pauseMarkerXs,
  stressBarHeights,
  topStressWord,
  wordCells,
  yDomain,
} from "./chartData";

describe("buildChartRows", () => {
  it("lấy độ dài nhỏ hơn của hai contour và giữ null", () => {
    expect(
      buildChartRows({
        ref: [0, null, 1.5],
        user: [0.2, 0.4],
        wordBounds: [0],
      }),
    ).toEqual([
      { x: 0, ref: 0, user: 0.2 },
      { x: 1, ref: null, user: 0.4 },
    ]);
  });

  it("contour rỗng cho ra danh sách rỗng", () => {
    expect(buildChartRows({ ref: [], user: [1], wordBounds: [] })).toEqual([]);
  });
});

describe("chartDrawable", () => {
  const points = (n: number, nulls = 0): (number | null)[] => [
    ...Array.from({ length: n }, (_, i) => i / 10),
    ...Array.from({ length: nulls }, () => null),
  ];

  it("9 điểm có giá trị ở một bên thì không vẽ", () => {
    expect(
      chartDrawable({ ref: points(10), user: points(9, 5), wordBounds: [0] }),
    ).toBe(false);
    expect(
      chartDrawable({ ref: points(9, 5), user: points(10), wordBounds: [0] }),
    ).toBe(false);
  });

  it("10 điểm có giá trị ở cả hai bên thì vẽ", () => {
    expect(
      chartDrawable({ ref: points(10), user: points(10, 3), wordBounds: [0] }),
    ).toBe(true);
  });
});

describe("yDomain", () => {
  const rows = (v: number) => [{ x: 0, ref: v, user: -v / 2 }];

  it("làm tròn lên số chẵn, tối thiểu 6, đối xứng", () => {
    expect(yDomain(rows(4.2))).toEqual([-6, 6]);
    expect(yDomain(rows(7.1))).toEqual([-8, 8]);
    expect(yDomain(rows(9))).toEqual([-10, 10]);
  });

  it("lấy giá trị tuyệt đối lớn nhất kể cả phía âm", () => {
    expect(yDomain([{ x: 0, ref: -7.1, user: 1 }])).toEqual([-8, 8]);
  });

  it("toàn null thì [-6, 6]", () => {
    expect(yDomain([{ x: 0, ref: null, user: null }])).toEqual([-6, 6]);
    expect(yDomain([])).toEqual([-6, 6]);
  });
});

describe("wordCells", () => {
  it("chia chiều rộng theo phần của wordBounds trên tổng số điểm", () => {
    expect(wordCells([0, 10, 25], 40)).toEqual([0.25, 0.375, 0.375]);
  });

  it("một từ chiếm trọn hàng", () => {
    expect(wordCells([0], 40)).toEqual([1]);
  });

  it("25 từ: tổng bằng 1 và mọi ô đều rộng hơn 0", () => {
    const bounds = Array.from({ length: 25 }, (_, i) => i * 4);
    const widths = wordCells(bounds, 100);
    expect(widths).toHaveLength(25);
    expect(widths.every((w) => w > 0)).toBe(true);
    expect(widths.reduce((a, b) => a + b, 0)).toBeCloseTo(1, 10);
  });

  it("hai ranh giới trùng nhau vẫn cho ô rộng hơn 0 và tổng bằng 1", () => {
    const widths = wordCells([0, 10, 10, 20], 40);
    expect(widths.every((w) => w > 0)).toBe(true);
    expect(widths.reduce((a, b) => a + b, 0)).toBeCloseTo(1, 10);
  });

  it("không có từ hoặc không có điểm thì rỗng", () => {
    expect(wordCells([], 40)).toEqual([]);
    expect(wordCells([0], 0)).toEqual([]);
  });
});

describe("stressBarHeights", () => {
  it("3 + 21 × z dương / z dương lớn nhất, trên cả ref và user", () => {
    expect(
      stressBarHeights([
        { ref: 1.2, user: -0.3 },
        { ref: 0.6, user: 0.6 },
      ]),
    ).toEqual([
      { ref: 24, user: 3 },
      { ref: 13.5, user: 13.5 },
    ]);
  });

  it("không có z dương nào thì mọi thanh là mẩu 3 px", () => {
    expect(
      stressBarHeights([
        { ref: -1, user: 0 },
        { ref: 0, user: -2 },
      ]),
    ).toEqual([
      { ref: 3, user: 3 },
      { ref: 3, user: 3 },
    ]);
  });

  it("rỗng thì rỗng", () => {
    expect(stressBarHeights([])).toEqual([]);
  });
});

describe("topStressWord", () => {
  it("trả chỉ số từ có stress.ref lớn nhất, hoà thì từ đầu", () => {
    expect(
      topStressWord([
        { ref: 0.2, user: 1 },
        { ref: 1.4, user: 0 },
        { ref: 1.4, user: 0 },
      ]),
    ).toBe(1);
  });

  it("rỗng thì null", () => {
    expect(topStressWord([])).toBeNull();
  });
});

describe("pauseMarkerXs", () => {
  const extraPause = (wordIndex: number): Issue => ({
    code: "EXTRA_PAUSE",
    wordIndex,
    data: { refMs: 40, userMs: 320 },
  });
  const flat: Issue = { code: "FLAT_PITCH", data: { pitchRange: 0.3 } };

  it("đặt dấu ‖ tại wordBounds[wordIndex + 1], bỏ qua mã khác", () => {
    expect(pauseMarkerXs([extraPause(1), flat], [0, 10, 25])).toEqual([25]);
  });

  it("từ cuối không có ranh giới kế tiếp thì không vẽ", () => {
    expect(pauseMarkerXs([extraPause(2)], [0, 10, 25])).toEqual([]);
  });

  it("nhiều dấu giữ thứ tự issue; không issue thì rỗng", () => {
    expect(pauseMarkerXs([extraPause(0), extraPause(1)], [0, 10, 25])).toEqual([
      10, 25,
    ]);
    expect(pauseMarkerXs([], [0, 10, 25])).toEqual([]);
  });
});

describe("chartAriaLabel", () => {
  it("bỏ dấu * của gợi ý", () => {
    expect(chartAriaLabel(["Nhấn vào *expect*, không phải *honestly*."])).toBe(
      "Ngữ điệu: đường xanh ngọc là bản gốc, đường cam là của bạn. Nhấn vào expect, không phải honestly.",
    );
  });

  it("nối nhiều gợi ý bằng khoảng trắng; không gợi ý thì không thừa khoảng trắng", () => {
    expect(chartAriaLabel(["A *x*.", "B."])).toBe(
      "Ngữ điệu: đường xanh ngọc là bản gốc, đường cam là của bạn. A x. B.",
    );
    expect(chartAriaLabel([])).toBe(
      "Ngữ điệu: đường xanh ngọc là bản gốc, đường cam là của bạn.",
    );
  });
});

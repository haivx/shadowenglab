import { describe, expect, it } from "vitest";
import { buildChartRows, chartDrawable, yDomain } from "./chartData";

describe("buildChartRows", () => {
  it("lấy độ dài nhỏ hơn của hai contour và giữ null", () => {
    expect(
      buildChartRows({ ref: [0, null, 1.5], user: [0.2, 0.4], wordBounds: [0] }),
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

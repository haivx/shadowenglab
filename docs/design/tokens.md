# Design tokens v0.2

Nguồn sự thật cho màu, chữ và hình khối. Giá trị nằm trong `tokens.css`; tài liệu này giải thích **khi nào dùng cái gì**.
Nền: Radix Colors (light) · component: shadcn/ui đổi token · tham khảo: Language Reactor, Elsa Speak, Superhuman, Strava.

## Quy tắc màu (quan trọng nhất)

Có hai hệ màu, **không bao giờ dùng lẫn**:

| Hệ | Ý nghĩa | Token | Dùng ở |
| --- | --- | --- | --- |
| Nhận diện nguồn | Teal = **Bản gốc**, cam = **Bạn** | `--original*`, `--you*` | Đường contour, nút "Nghe bản gốc / của bạn", hàng âm, chú thích biểu đồ |
| Điểm số | Đỏ = kém, vàng = tạm được, xanh lá = đủ tốt, xám = bản gốc không đủ rõ | `--score-*` | Điểm tổng, 3 chỉ số, điểm từng từ, điểm trong transcript, thanh tiến độ, xu hướng lỗi |

Ngưỡng điểm (hiệu chỉnh lại sau eval, P7):

| Mức | Khoảng | Màu chữ | Gạch chân / thanh | Nền nhạt |
| --- | --- | --- | --- | --- |
| good | ≥ 80 | `--score-good-text` | `--score-good` | `--score-good-soft` |
| ok | 60–79 | `--score-ok-text` | `--score-ok` | `--score-ok-soft` |
| bad | < 60 | `--score-bad-text` | `--score-bad` | `--score-bad-soft` |
| unrated | bản gốc không đủ rõ | `--score-unrated-text` | gạch đứt `--score-unrated` | `--muted` |

- Luôn có **số đi kèm màu**; không truyền đạt ý nghĩa chỉ bằng màu.
- Đỏ còn dùng cho trạng thái **đang ghi** (`--recording`) và lỗi hệ thống (`--destructive`).
- Biểu đồ nhiều chuỗi không mang nghĩa điểm (ví dụ Âm / Ngữ điệu / Nhịp theo tuần) dùng `--series-1..3`.
- Mọi màu chữ trên nền trắng đạt tương phản ≥ 4.5:1 (bậc 11–12 của Radix). Không dùng bậc 9 cho chữ nhỏ.

## Chữ

| Vai trò | Font | Cỡ / độ đậm | Ví dụ |
| --- | --- | --- | --- |
| Tiêu đề trang | Figtree | 32–34 / 800, letter-spacing −0.03em | "Thư viện" |
| Câu đang tập | Figtree | 38 / 600, −0.015em | câu tô màu trong Phòng tập |
| Số lớn (kiểu Strava) | Figtree | 52–72 / 800, −0.04em, line-height 0.9–1 | điểm tổng 74 |
| Số phụ | Figtree | 22–24 / 700 | 86 tốc độ |
| Thân | Figtree | 14–16 / 400–600 | gợi ý, danh sách |
| Nhãn nhóm | Figtree | 12 / 700, uppercase, 0.06–0.08em, `--slate-9` | "TRANSCRIPT · 32 CÂU" |
| Mốc thời gian, điểm nhỏ, kbd | JetBrains Mono | 11–13 / 500 | `00:41`, `78` |
| IPA | Noto Sans | 15–18 / 400–500 | /ən ˈɑnɪstli/ |

## Hình khối và khoảng cách

- Bo góc: 6 (badge, kbd) · 8 (nút, input, chip) · 12 (khối lớn) · 16 (dialog).
- **Không shadow.** Tách nhóm bằng khoảng trắng và đường kẻ `--border` (slate-4); chỉ dùng nền `--slate-2` cho khối cần nổi (cột transcript).
- **Ít card**: chỉ dùng card khi phần tử là một đối tượng độc lập (bài trong Thư viện). Số liệu tổng kết là hàng số lớn giữa hai đường kẻ, không đóng khung.
- Khoảng cách theo bội số 4; giữa các khối lớn 24–32.

## Nút và thao tác

- Web app: **nút là cách thao tác chính**, phím tắt là phụ.
- Mọi hành động có nút có chữ, cao 44px (thường) hoặc 48px (hành động chính trong thanh dưới). Nút chỉ có icon phải có `aria-label` và `title` chứa phím tắt.
- Biến thể (theo Radix Themes): `solid` (slate-12, hành động chính, tối đa 1–2 mỗi vùng) · `soft` (nền màu nhạt, ví dụ nghe bản gốc / của bạn) · `outline` · `ghost`.
- Phím tắt hiện dạng `<kbd>` nhỏ trong nút và trong tooltip, không có thanh phím tắt riêng.

## Map sang Tailwind

```js
// tailwind.config.ts (trích)
theme: {
  extend: {
    colors: {
      original: { DEFAULT: 'var(--original)', text: 'var(--original-text)', soft: 'var(--original-soft)' },
      you:      { DEFAULT: 'var(--you)',      text: 'var(--you-text)',      soft: 'var(--you-soft)' },
      score: {
        good: { DEFAULT: 'var(--score-good)', text: 'var(--score-good-text)', soft: 'var(--score-good-soft)' },
        ok:   { DEFAULT: 'var(--score-ok)',   text: 'var(--score-ok-text)',   soft: 'var(--score-ok-soft)' },
        bad:  { DEFAULT: 'var(--score-bad)',  text: 'var(--score-bad-text)',  soft: 'var(--score-bad-soft)' },
        unrated: { DEFAULT: 'var(--score-unrated)', text: 'var(--score-unrated-text)' },
      },
      recording: 'var(--recording)',
    },
    fontFamily: { sans: ['var(--font-sans)'], mono: ['var(--font-mono)'], ipa: ['var(--font-ipa)'] },
    borderRadius: { sm: 'var(--radius-sm)', DEFAULT: 'var(--radius)', lg: 'var(--radius-lg)', xl: 'var(--radius-xl)' },
  },
}
```

Hàm dùng chung (đặt trong `packages/contracts` hoặc `apps/web/lib`): `scoreLevel(score: number | null): 'good' | 'ok' | 'bad' | 'unrated'`, để mọi màn dùng cùng ngưỡng.

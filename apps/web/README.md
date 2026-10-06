# apps/web — App chính (Next.js 14)

Thư viện, tạo bài, phòng tập, ôn luyện, tiến bộ, settings.
Spec UI: `docs/design/` · flow: `docs/flows.md` (F0–F4) · trình phát dùng XState (`docs/decisions/0001-uv-va-xstate.md`).

## Trạng thái sau P0

Khung Next 14 (App Router) rỗng: `app/layout.tsx` và `app/page.tsx` chỉ hiện tên app. Chưa có màn hình hay component nào. UI bám `docs/design/` được dựng từ Phase 2 (GSD); không thêm màn hay component ngoài thiết kế đã chốt.

`app/page.tsx` import `LessonStatus` từ `@shadowenglab/contracts` và in số trạng thái ra một data attribute. Đây chỉ là bằng chứng wiring: `next.config.mjs` có `transpilePackages: ["@shadowenglab/contracts"]` nên package contracts (chỉ có TypeScript nguồn) import được trực tiếp, và `pnpm --filter @shadowenglab/web build` chạy được.

## Chạy

```bash
make dev                                  # FastAPI :8000 + web http://localhost:3000
pnpm --filter @shadowenglab/web dev       # chỉ web, cổng 3000
pnpm --filter @shadowenglab/web build
```

`make lint` kiểm tra file của app này bằng ESLint 9 (flat config ở gốc repo). `next build` bỏ qua ESLint (`eslint.ignoreDuringBuilds`) vì plugin Next 14 crash với ESLint 9.

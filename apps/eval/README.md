# apps/eval — App eval cho người chấm bản xứ (Next.js + Supabase, deploy Vercel)

Spec: `docs/product.md` mục 4 · flow F5 · màn E1–E4 trong `docs/design/`.

## Trạng thái sau P0

Khung Next 14 (App Router) rỗng, giao diện tiếng Anh: `app/layout.tsx` và `app/page.tsx` chỉ hiện tên app. Dùng chung `tsconfig.base.json` và import được `@shadowenglab/contracts` qua `transpilePackages`. Chưa có đăng nhập, Supabase hay màn chấm nào; app được dựng ở P5 (Phase 6 trong GSD).

## Chạy

```bash
make dev-eval                              # http://localhost:3001
pnpm --filter @shadowenglab/eval dev       # tương đương, cổng 3001
```

Hợp đồng dữ liệu với app chính (`ClipManifest`, `Label`) nằm ở `packages/contracts/src/eval.ts`.

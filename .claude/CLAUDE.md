<!-- GSD:project-start source:PROJECT.md -->

## Project

**ShadowEngLab**

Web app chạy local để Liam tự luyện shadowing tiếng Anh (giọng Mỹ) từ bất kỳ video YouTube nào: dán link, tập từng câu, và biết chính xác mình nói khác **chính người nói trong video** ở đâu (âm, trọng âm, lên xuống giọng, ngắt nghỉ), kèm gợi ý cụ thể để sửa. Đi kèm một app eval nhỏ deploy online để 2 người chấm bản xứ kiểm chứng điểm của hệ thống (human review).

Spec sản phẩm chi tiết: `docs/product.md` (nguồn sự thật cấp sản phẩm). Luồng: `docs/flows.md`. UI: `docs/design/`.

**Core Value:** Sau mỗi lượt nói, Liam biết **đáng tin** mình lệch khỏi người nói gốc ở đâu — so audio với audio gốc, precision trước recall: khi không chắc thì không báo lỗi.

### Constraints

- **Tech stack (khoá):** Next.js 14 + TS strict + Tailwind + shadcn/ui (token Radix, `docs/design/tokens.md`) + TanStack Query + Recharts + XState; FastAPI + Python 3.11 qua uv; SQLite + file system; app eval Next.js + Supabase trên Vercel — ADR 0001, product.md mục 5
- **Nền tảng:** macOS Apple Silicon (mlx-whisper); cần Node ≥ 22.13, pnpm 11.9, uv, ffmpeg, espeak-ng
- **Hiệu năng:** chấm một câu ≤ 3 s (chỉ xử lý audio người học; feature bản gốc tính sẵn khi tạo bài); tạo bài từ video 5 phút ≤ 5 phút
- **Chi phí:** local-first, ~$0–1/tháng; chỉ OpenAI (gợi ý, TTS) là trả phí và tuỳ chọn
- **Chạy khi thiếu key:** thiếu `OPENAI_API_KEY` → gợi ý template, tắt TTS, không chặn app
- **Contract-first:** `packages/contracts` (Zod) là nguồn sự thật; Liam chốt contract trong Discuss trước khi Plan; Claude không tự đổi contract, schema DB, ngưỡng chấm hay model
- **Eval gate:** từ P3 trở đi mọi thay đổi model/ngưỡng/rule phải chạy `make eval` và dán bảng metric vào PR
- **Dữ liệu:** không commit audio eval, nhãn thô người chấm, `.env`
- **UI:** bám `docs/design/`; không thêm màn/component ngoài thiết kế đã chốt; nút là chính, phím tắt phụ; màu điểm qua `scoreLevel()` (đỏ < 60, vàng 60–79, xanh ≥ 80); teal/cam chỉ cho Bản gốc/Bạn
- **Code style:** TS không `any`, Zod ở mọi ranh giới I/O; Python type hints + ruff + pytest, hàm audio thuần (array in → array out)
- **Quy trình:** mỗi phase đủ Discuss → Plan → Execute → Verify → Ship; PR nhỏ, review tại ranh giới (schema, state machine, output pipeline); quyết định mới → ADR trong `docs/decisions/`

<!-- GSD:project-end -->

<!-- GSD:stack-start source:STACK.md -->

## Technology Stack

Technology stack not yet documented. Will populate after codebase mapping or first phase.
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-fast` for a trivial task inline, with no subagents and no PLAN.md
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->

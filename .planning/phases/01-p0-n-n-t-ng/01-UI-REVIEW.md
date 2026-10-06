# Phase 1 — UI Review

**Audited:** 2026-10-06
**Baseline:** Abstract 6-pillar standards (no UI-SPEC.md for P0; design spec exists in `docs/design/` but no implementation required in this phase)
**Screenshots:** Not captured (no dev server running on localhost:3000, 5173, or 8080)
**Interaction captures:** off (workflow.ui_interaction_capture is false)

---

## Audit Context

**Phase 1 (p0-n-n-t-ng) is a foundation/infrastructure phase (P0).** Per `01-CONTEXT.md`:

> "Thiết kế UI của P0 **đã xong** (`docs/design/`), không thuộc phạm vi còn lại. Không có UI nào được dựng trong phase này (chỉ khung Next.js rỗng cho `make dev`)."

**No UI implementation was planned or executed in this phase.** Only a Next.js skeleton exists for the dev server. Real UI implementation begins in P1 (UI/UX phase).

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 3/4 | Minimal text only ("ShadowEngLab"); no placeholder language or generic terms, but no actual copy to evaluate |
| 2. Visuals | 1/4 | Single h1 on blank page; no visual hierarchy, no focal point, no design system applied |
| 3. Color | 1/4 | No CSS or design tokens implemented; browser defaults only; no color system applied |
| 4. Typography | 1/4 | Browser default fonts and sizing only; no Tailwind or font system; no design token usage |
| 5. Spacing | 1/4 | Browser default spacing only; no Tailwind, CSS Grid, or design-system classes; no structured layout |
| 6. Experience Design | 1/4 | Static h1 with no interactive elements; no loading states, error boundaries, empty states, or disabled state handling |

**Overall: 8/24** (33%)

---

## Top 3 Priority Fixes

1. **Implement design tokens and Tailwind configuration** — The design system tokens (`docs/design/tokens.md`) are defined but not applied to the Next.js app. No tailwind.config.ts file exists, no font families loaded, no color palette mapped. _Fix:_ Create `apps/web/tailwind.config.ts`, map tokens to Tailwind theme colors/fonts, import design tokens CSS in global stylesheet, verify token output matches `docs/design/tokens.css`.

2. **Add global styling and layout structure** — No CSS file imports, no body/html baseline styles, no layout container or grid structure. The page is bare HTML with browser defaults. _Fix:_ Create `apps/web/app/globals.css` with Tailwind directives, establish spacing scale (4px base unit), set font family and line-height, import fonts (Figtree for body, JetBrains Mono for code, Noto Sans for IPA per tokens.md).

3. **Create minimal component library structure** — No UI components exist beyond the h1; no button, card, badge, or form component examples from the design spec. _Fix:_ Create `apps/web/components/` directory structure with at least Button and Card components following Radix Themes variant pattern (solid, soft, outline, ghost per tokens.md), then demonstrate in home page with proper spacing, colors, and hover states.

---

## Detailed Findings

### Pillar 1: Copywriting (3/4)

**Finding:** Minimal text surface area; no issues with generic labels, but minimal content to audit.

- Home page contains only "ShadowEngLab" as the page title (metadata) and in an `<h1>` heading
- No CTA buttons, placeholder text, or error/empty state copy exists
- No generic patterns detected (`Click Here`, `Submit`, `OK`, `No data`, `went wrong`, etc.)
- Language is accurate and intentional ("ShadowEngLab" is the product name)

**Evidence:** `apps/web/app/page.tsx:5-7` shows only `<h1>ShadowEngLab</h1>` with no additional text content.

**Rationale:** Score is 3/4 (not 4/4) because there is no actual copy to evaluate beyond a title. The phase explicitly did not implement UI, so absence of copy is expected, not a defect. When UI is implemented in P1, copywriting must be audited against the planned component labels in `docs/design/components.md`.

---

### Pillar 2: Visuals (1/4)

**Finding:** No visual hierarchy, no focal point, no component structure, no design system applied.

- Single `<h1>` centered by browser default only
- No spacing, padding, or layout structure
- No color differentiation (all text is black on white)
- No icon usage, no image, no visual weight variation
- No baseline grid or design discipline

**Evidence:**
- `apps/web/app/layout.tsx:6-11` — root layout contains only `<html>`, `<body>`, and `{children}` with no CSS
- `apps/web/app/page.tsx:5-7` — home page is only `<main>` with one `<h1>` tag

**Missing visual patterns from design spec:**
- No ScoreHero (large number display per tokens.md "Số lớn" style: 52–72px, Figtree 800)
- No IntonationChart component structure
- No TipList layout
- No LessonCard examples
- No JobSteps progress indicator

**Rationale:** Score 1/4 indicates the pillar is not met. A visual foundation must include hierarchy (size, weight, color, position), focal point, and layout structure. None exist.

---

### Pillar 3: Color (1/4)

**Finding:** No color system implemented; no design tokens loaded; no Tailwind theme configuration.

- No CSS file imports in layout or page
- No `globals.css` or stylesheet reference
- No Tailwind classes used (no `text-*`, `bg-*`, `border-*`, etc.)
- No design token CSS variables referenced (`--original`, `--score-good`, etc.)
- All text renders in browser default black on white

**Evidence:**
- `apps/web/app/layout.tsx` — no `<link>` to CSS, no `import` of stylesheet
- `apps/web/app/page.tsx` — no className or style attributes on any element
- No `apps/web/tailwind.config.ts` file exists
- No color mapping from `docs/design/tokens.md` found in codebase

**Design contract deviation:**
Per `docs/design/tokens.md`, the design requires:
- Source ID colors: `--original` (teal), `--you` (orange)
- Score colors: `--score-good` (≥80, green), `--score-ok` (60–79, yellow), `--score-bad` (<60, red), `--score-unrated` (gray)
- All colors mapped to Tailwind via `theme.extend.colors`
- Accessibility minimum: 4.5:1 contrast on all text

None of this is present.

**Rationale:** Score 1/4 because the color pillar is completely absent. Implementing means: (1) Tailwind config with token color mappings, (2) globals.css importing token CSS, (3) applying classes to components, (4) verifying WCAG AA contrast.

---

### Pillar 4: Typography (1/4)

**Finding:** No font system, no font family setup, no sizing scale applied.

- No font files loaded or imported
- No `<link>` to Google Fonts, no @font-face declarations
- All text uses browser default font (typically serif or system sans-serif)
- No Tailwind text size classes (no `text-sm`, `text-base`, `text-2xl`, etc.)
- No font weight variation (no `font-bold`, `font-semibold`, etc.)

**Evidence:**
- `apps/web/app/layout.tsx` — no `<link rel="preload">` for fonts, no Tailwind import
- No font definitions in Tailwind config (file does not exist)
- `docs/design/tokens.md` specifies three font families required:
  - **Figtree** (sans-serif, primary): used for titles (32–34px, 800wt), body (14–16px, 400–600wt), large numbers (52–72px)
  - **JetBrains Mono** (monospace): used for time, scores, kbd (11–13px, 500wt)
  - **Noto Sans** (specific): used for IPA (15–18px, 400–500wt)
  - None are loaded.

**Missing typography scale per tokens.md:**
- Page title: 32–34px, 800wt, letter-spacing −0.03em
- Section heading: 38px, 600wt, −0.015em
- Large numbers: 52–72px, 800wt, line-height 0.9–1
- Body: 14–16px, 400–600wt
- Label: 12px, 700wt, uppercase

Current implementation uses only browser default (likely ~16px serif).

**Rationale:** Score 1/4 because the typography pillar is not implemented. Implementation requires: (1) font CDN or local files, (2) Tailwind `fontFamily` configuration, (3) text size and weight classes on components.

---

### Pillar 5: Spacing (1/4)

**Finding:** No spacing system; no Tailwind spacing scale; browser default margins only.

- No padding classes (no `p-*`, `px-*`, `py-*`)
- No margin classes (no `m-*`, `mx-*`, `my-*`)
- No gap or space-between classes
- No structured layout (no Grid, Flex with explicit gaps)
- No baseline 4px spacing unit applied

**Evidence:**
- `apps/web/app/page.tsx:5-7` — `<main>` and `<h1>` have no className attributes
- No CSS file with spacing declarations
- Browser default spacing only (margins vary by element type)

**Design contract violations:**
Per `docs/design/tokens.md` §"Hình khối và khoảng cách":
- Spacing should be **multiples of 4px** (4, 8, 12, 16, 20, 24, 28, 32, etc.)
- Large block separation: 24–32px
- Border radius: 6px (badge), 8px (button), 12px (block), 16px (dialog)
- None specified in current code.

**Rationale:** Score 1/4 because spacing is completely absent. Implementation requires: (1) Tailwind spacing scale (extend defaults if needed), (2) component padding/margin classes, (3) gap/flex layout classes for container structure.

---

### Pillar 6: Experience Design (1/4)

**Finding:** No interactive elements, no state handling, no error/loading/empty state UI.

- Page is entirely static HTML
- No button or interactive component
- No React hooks (useState, useEffect) for state
- No loading states (no spinner, skeleton, or loading placeholder)
- No error boundaries or error UI
- No empty states (no "No lessons yet" message or placeholder)
- No disabled states for buttons or form controls (no buttons exist)
- No confirmation for destructive actions (no delete/cancel patterns)

**Evidence:**
- `apps/web/app/page.tsx` — only imports `LessonStatus` from contracts for data-attribute but uses no state or interaction
- No context providers, error boundaries, or suspense boundaries
- No form inputs or buttons requiring validation feedback

**Design patterns missing per `docs/design/components.md` and flows:**
- F1 (Job progress): requires JobSteps component with loading states (queued → downloading → separating → transcribing → ready/failed)
- F2 (Scoring): requires loading spinner while processing, error fallback on API failure, empty list when no lessons
- LessonCard: requires hover state, click action
- Recording interactions: require recording started/stopped states, timer display

**Rationale:** Score 1/4 because Experience Design is completely absent. Implementation requires: (1) components with interactive state, (2) loading/error/empty patterns, (3) error boundaries, (4) disabled/hover/active state styles, (5) confirmation UI for risky actions.

---

## Files Audited

- `apps/web/package.json` — workspace reference, Next 14.2.35, React 18.3.1 (no extra UI libraries)
- `apps/web/tsconfig.json` — (checked: standard Next.js config)
- `apps/web/app/layout.tsx` — root layout, no styling or imports
- `apps/web/app/page.tsx` — home page, single h1, no components
- `apps/web/next-env.d.ts` — (auto-generated, no manual code)

**Total files examined:** 5 (app files) + 1 (design spec reference)

---

## Registry Safety Audit

`components.json` does not exist in `apps/web`. shadcn/ui has not been initialized. No third-party registries to audit.

---

## Conclusion

Phase 01 is a **foundation/P0 phase** that explicitly deferred all UI implementation to Phase 1 (P1). The current state is an intentional Next.js skeleton with no design system, styling, components, or interactions.

**This is not a defect.** Phase 01 delivered:
- Contract definitions (Zod/JSON Schema/pydantic) ✓
- FastAPI backend with routes ✓
- Audio processing pipeline ✓
- Makefile and dev tooling ✓
- Design tokens specification (not implementation) ✓

**UI implementation is planned for P1**, at which point this review will measure conformance to `docs/design/tokens.md` and component specs.

**Current blockers for P1:**
1. Tailwind config and token mapping
2. Font loading and typography scale
3. Global stylesheet with baseline styles
4. Component library (Button, Card, Badge, Input, etc.)
5. Page layouts for LessonCard, ScoreHero, IntonationChart
6. Interactive state management and loading/error patterns

---

*Phase: 01-p0-nen-tang*
*Reviewed: 2026-10-06*

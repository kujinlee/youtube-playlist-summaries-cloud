# Codex Adversarial Review — Slide Auto-Crop Implementation Plan

**Date:** 2026-06-29
**Model:** gpt-5.5 (fresh session)
**Target:** `docs/superpowers/plans/2026-06-29-dig-slide-autocrop.md`
**Outcome:** Completed cleanly. 2 Blocking, 2 High, 3 Medium, 2 Low. Several items explicitly CHECKED-OK.

---

## Blocking

**PB1 — CSS crop math wrong for real slides (Task 5).** `aspect-ratio:1 / keepFrac` ignores natural width/height; correct is `naturalWidth / (naturalHeight × keepFrac)`. For 1280×720, trimTop=.25/trimBot=.05 → plan makes a 1.43:1 box vs the true 2.54:1 kept band; `object-fit:cover` then scales by height and crops **horizontally**, breaking the vertical-only guarantee.
Fix: capture native `width`+`height` (ffprobe), emit `aspect-ratio:${width}/${height*keepFrac}`; derive the width cap from natural dims.

**PB2 — New test files not discovered by Jest.** `jest.config.ts` matches only `tests/lib/**`, `tests/api/**`, `tests/scripts/**`, `tests/components/**`, `tests/smoke.test.ts`. The plan's `lib/dig/*.test.ts` etc. live outside `tests/` → never run.
Fix: place all unit/integration tests under `tests/lib/dig/` and `tests/lib/html-doc/`; fix imports.

## High

**PH1 — Required `cropMap` breaks 47 existing call sites.** 1 route + 31 in `tests/lib/html-doc/render-dig-deeper.test.ts` + 15 in `tests/e2e/dig-deeper.spec.ts`; `tsconfig` includes all `**/*.ts` → build breakage.
Fix: make `cropMap?` optional, defaulting to `new Map()` inside `renderDigDeeperDoc`.

**PH2 — Playwright spec path wrong.** `playwright.config.ts` `testDir: './tests/e2e'`. Plan used `e2e/`.
Fix: `tests/e2e/dig-slide-crop.spec.ts`.

## Medium

**PM1 — Cross-process cache lost-update.** In-process promise chain serializes one Node process only; two Next workers can read→add→rename, last wins, dropping an entry. Atomic rename prevents torn JSON, not lost updates.
Resolution (adopted): document + test that a cross-process race causes only a **recompute** (deterministic, cheap), never corruption. No lockfile (YAGNI).

**PM2 — `width:min(100%,640px)` bakes in 16:9.** Fix: `min(100%, ${Math.round(360*width/height)}px)` (folds into PB1).

**PM3 — E2E fixture placeholders unresolvable.** Specify exact setup mirroring `tests/e2e/dig-deeper.spec.ts` (route.fulfill with HTML generated from a deterministic `cropMap`).

## Low

**PL1 — Missing "heading-flush/content-to-bottom" unit test** claimed in spec table. Add it to Task 1.
**PL2 — Zoom cursor on `<figure>` but handler binds to `img.dig-slide`** (render-dig-deeper.ts:310-313). Clicking the figure border shows zoom cursor but does nothing. Fix: scope `cursor:zoom-in` to the img only.

## Checked — OK
- Route wiring: `summaryMdPath` (route.ts:145) passed at :195; `dug` in scope :185-193; `GET` already async.
- Lightbox nesting: handler `e.target.classList.contains('dig-slide')` still fires on the nested img.
- `object-position` formula correct once aspect-ratio fixed.
- Task 1 computeTrim test math consistent with PAD/MIN constants.
- Task 2 ffmpeg geq escaping correct for execFile argv; rawvideo = exactly height bytes; length check fails closed.
- Task 2 real-ffmpeg integration runs once files are under `tests/lib`; committed PNG fixture acceptable.

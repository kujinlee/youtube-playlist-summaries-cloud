# Adversarial Review — Plan: Dig Image Sizing (Feature 1)

**Reviewer:** Claude adversarial subagent (fresh, full file access; every cited line verified against real files).
**Date:** 2026-06-28
**Codex gap:** Codex CLI at usage limit; this Claude adversarial review satisfies the Post-Plan Gate (AFK). Re-attempt before merge if access returns.

**Verdict: APPROVE — no Blocking. 2 Medium + 3 Low, all addressed in plan rev 2 or deferred to verification.**

## Verified accurate (every line ref)
`.dug img{margin:2em 0}` at `render-dig-deeper.ts:132`; success `<img>` return at `:118`; other branches at `:108`/`:115`/`:122`; `expandAllDialogs` ends `:263`; shell return `:265–285`; `.dg img` generic rule `:48`; test assertion `render-dig-deeper.test.ts:847`; `MINIMAL_JPEG`/`makeTempDir`/`renderDigDeeperDoc` signatures real; `nav.ts:304` Esc local to expand-all; `makeCompanionHtmlWithSlides()` at `dig-deeper.spec.ts:78` renders a base64 `<img>`.

- **CSS specificity** `.dg img.dig-slide` (0,0,2,1) beats `.dg img` (0,0,1,1) — confirmed; downscale + inherited rules correct.
- **Q1 success branch** — traced buildRenderer containment: asset resolves inside assetsRoot, `readFileSync` succeeds → returns the `dig-slide` `<img>`; regex passes.
- **Q2 fixture renders image** — `mergeDigDoc` matches `timeRange.startSec=10 === DugSection.sectionId=10`; `.dug` block renders; minimal `timeRange` runtime-safe (`as unknown as` hides nothing).
- **Q3 no CSS-removal regression** — only `.dug img` dependents are line 132 + its test 847 (both updated); no `dg-zoom`/`9500` collisions.
- **Q4 zoom script** — no `stopPropagation` in nav.ts; `.dig-slide` click bubbles to document → zoom fires; open-click `return`s before close branch; backdrop `t===ov` correct; zoomed img inert.
- **Q5 Esc coexistence** — new handler early-returns unless `data-open`; additive with nav's local Esc regardless of order.
- **Task ordering** — TDD order correct; the `.dug img` rule + test update happen in the same task (no red window); Task 2 depends on Task 1's class. `playwright.config.ts` auto-starts the dev server (`reuseExistingServer`); `page.route` stub intercepts → Z-tests need no real data.

## Findings + disposition
- **M1 — backdrop click position fragility.** → Addressed: added a comment documenting the centered-flex assumption; on the default 1280×720 viewport the (5,5) corner has a ≥32px backdrop margin (image capped at 95vw/95vh).
- **M2 — `margin:2em auto` centering is layout-conditional.** → Deferred to Phase-4 verification (eyeball centering on a real doc); noted in the plan.
- **L1 — Z1 bundled all dismissals in one block.** → Addressed: split into Z0 (Esc-when-closed), Z1 (backdrop), Z2 (Esc), Z3 (✕), one block per path (dev-process E2E rule).
- **L2 — close button not asserted in jest presence test.** → Addressed: added `toContain('id="_dg-zoom-close"')`.
- **L3 — no focus-trap/`aria-hidden`.** → Out of scope; noted as an a11y follow-up.

Nothing gates the build; a fresh implementer following the plan commits green.

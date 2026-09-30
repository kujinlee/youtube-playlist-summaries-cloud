---
name: page-chrome-seam-merged
description: "FIRES-WHEN: citing PR #185, page chrome, or the provenance stamp — ⭐ PR #185 (7183111) 2026-08-31 — theme control + provenance stamp + refresh across all five page producers. NOTHING in the repo ever had a toggle; I told the user two pages did, having counted CSS SELECTORS as controls. A guard's docstring carried the same false claim"
metadata:
  node_type: memory
  type: project
---

**MERGED 2026-08-31 — PR #185, squash `7183111`.** Backlog **#76** + **#77**. Master re-verified
after the squash: page_chrome 47/47, gen-dashboard 217/217, brief-compose 40/40, explainer-serve
71/71, gen-backlog-page 71/71, gen-goals-page 15/15, `--mutate .` **5 files / 105 mutations / 0
survivors**. (#75, the ordering fix, shipped separately as PR #184 / `3cc3677`.)

## The correction, which is the memorable part

I told the user two pages already had a theme toggle. **None ever did.** I had counted
`:root[data-theme="dark"]` **CSS selectors** as controls; `setAttribute('data-theme')` returned zero
hits repo-wide. And `gen-backlog-page.py:1520` — a real guard's docstring — asserted the toggle
existed and checked four palettes on that basis. Same family as
[[true-about-the-name-silent-about-the-layer]]: **a claim about a mechanism needs a search, not a
read**, and I made the claim out loud before measuring.

## Design, reusable

**MECHANISM SHARED, PALETTE LOCAL.** `scripts/page_chrome.py` owns the attribute, button,
persistence and OS fallback; each page keeps its own colours. Which creates the fail-silent it must
prevent — a control over a page with no `data-theme` palette changes an attribute nothing styles —
so **`assert_wired()` gates every write**. That check, not the button, is the load-bearing part.

⚠ **PREREQUISITE, and the reason the slice paused mid-way:** `gen-dashboard` read its palettes
POSITIONALLY (`css.split("prefers-color-scheme:dark")[1]`). Adding `data-theme` blocks would have
left the contrast guard checking the OLD palettes while reporting green — *the same defect as #76
itself*. Fixed before anything went live. ⚠ The rework left the suite at an unchanged 213/213, which
proved only the OLD path survived; the new branch was measured separately **with a control** —
legible palette 0 reports, illegible 12.

⚠ **`provenance()` lives in the seam**, because `gen-goals-page` already had its own (commit date +
sha, no generation time, no dirty flag). Two pages computing "what was this built from" two ways is
the drift the module exists to stop.

## Review round 1 — 7 findings, 2 High, both in code written to prevent that class

`assert_wired` accepted ANY script containing `"chrome-theme"` (`console.log("chrome-theme")` passed
with no handler) → the emitter now writes `CHROME_SCRIPT_MARK` and the check requires that. The
composer trusted the button id alone → an inert control with no stamp. **Then my fixes cost two
more, both found by `--mutate .`**: a stale manifest anchor, and a caught mutation becoming a
SURVIVOR because nothing distinguished the marker *inside a `<script>`* from *anywhere on the page*.
My composer-fix test fixture was itself a bare button — the defect, sitting in its own test.

## ⭐ Driven, not read

Both reviewers marked `chrome_script()` NOT CHECKED. Pressed in Chrome on the served page: `dark →
light → dark`, background `rgb(20,24,27)` ↔ `rgb(247,248,250)`, persisted and reapplied before paint
after reload, refresh POSTed and rebuilt. **The provenance flag was watched CHANGING** —
`4572635 · uncommitted changes` → `0b5284d` — which no unit case can show.

⚠ **Residual, stated in the PR:** that browser run was by hand ONCE. Nothing re-runs it, so a future
change could break the click path with every suite green.

See [[a-costbenefit-finding-expires-when-the-denominator-moves]],
[[mutation-harness-home-redirect-state]].

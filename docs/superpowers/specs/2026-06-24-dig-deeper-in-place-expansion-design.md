# Dig-Deeper v2 — In-Place Section Expansion

**Date:** 2026-06-24
**Branch:** `feat/section-dig-deeper-screenshots` (continuation; follows PR #23)
**Supersedes interaction model of:** `2026-06-24-section-dig-deeper-screenshots-design.md`
**Status:** Approved (brainstorming) — pending implementation plan

---

## 1. Problem & Motivation

PR #23 shipped the first dig-deeper feature: an on-demand, per-section elaboration of a
summary, with slide screenshots, stored in a `<base>-dig-deeper.md` companion file. User
validation against the live PR returned seven issues. This spec addresses them, with the
centerpiece being a redesign of the dig-deeper **document model**.

### Validation findings (from user)

| # | Item | Disposition |
|---|------|-------------|
| 1 | Some HTML docs show no dig-deeper menu | **Fix** — stale cached summary HTML (see §6) |
| 2 | "Can't find the file" for a dig-deeper URL | **No bug** — file is `<slug>-dig-deeper.md` in `raw/`; user searched the *videoId*, but filenames are slug-based (videoId→slug via `playlist-index.json`). Documented, no code change. |
| 3 | Are embedded images robust? | **Keep base64-inline** + add missing-asset guard (see §4) |
| 4 | Slide has speaker/branding; want clean full-width slide | **Deferred** — keep full-frame capture as-is for now |
| 5 | Returning to summary forces a new tab | **Fixed by redesign** — all navigation becomes same-tab (see §5) |
| 6 | Sections not spaced enough | **Fix** — CSS spacing (see §4) |
| 7 | Mirror summary structure; expand sections in place | **Redesign** — the core of this spec (see §3–§5) |

### Root causes confirmed during exploration

- **#7:** The companion doc is an upsert accumulator of **only dug sections**
  (`lib/dig/companion-doc.ts`). Un-dug sections do not appear. A summary with 7 sections
  whose user dug 5 yields a dig doc with 5 sections; sections 6 and "Conclusion" are absent.
- **#5:** Asymmetric navigation. "view detail ↓" opens a **new tab** (`target="_blank"`,
  commit `2a3bfc7`), but "↑ summary" navigates the **current tab** (`location.href`).
  Returning to summary replaces the dig tab; re-digging then spawns yet another new tab.
- **#1:** `app/api/html/[id]/route.ts` serves `type=summary` from a **pre-built cached file**
  (`htmls/<slug>.html`) with **no version check**. The KO doc's cache (mtime Jun 23 09:25)
  predates the dig feature → has `▶` timestamp links but **zero** dig controls. The EN doc
  (mtime Jun 24 17:23) was re-exported after the feature → has 7 dig controls. The renderer
  and parser are correct; the served artifact is stale.

---

## 2. Goals & Non-Goals

### Goals
- The dig-deeper doc presents **every** summary section, in summary order, showing the
  summary gist by default and expandable to the dug elaboration **in place**.
- Per-section compare: toggle a dug section between its summary gist and its dug elaboration
  with no refetch.
- "Expand all" generates all remaining sections (guarded by a confirm dialog).
- All navigation is **same-tab**; no tab proliferation.
- Stale summary HTML self-heals (lazy, version-gated) so the dig menu always appears.
- No migration of existing dig companion files.

### Non-Goals
- Slide cropping / removing speaker & branding from frames (#4) — deferred.
- Retiring the legacy `-deep-dive.md` document — out of scope (separate decision).
- Changing the dig **generation** pipeline (Gemini REST, yt-dlp/ffmpeg slide extraction) —
  reused as-is.

---

## 3. Document Model & Data Flow (Approach 1: thin companion + render-time merge)

The companion `<base>-dig-deeper.md` remains a **delta store of only dug sections** — its
sentinel-delimited format (`<!-- dig-section: <id> -->`) is **unchanged**. The dig-deeper
doc structure is assembled at **render time** by merging three already-existing inputs.

### Inputs (all derivable from the companion path)
| Input | Source | Provides |
|---|---|---|
| Summary markdown | `<base>.md` → `parseSummaryMarkdown` | Section order, numerals, titles, `timeRange.startSec` |
| Magazine model | `models/<base>.json` (`MagazineModel`) | Per-section `lead` + `bullets` (the gist, identical to the summary doc) |
| Dig companion | `<base>-dig-deeper.md` | Dug sections (elaboration markdown + `assets/` slide refs), keyed by `sectionId` = `startSec` |

`<base>` is recovered from the companion filename (`<base>-dig-deeper.md`); the summary,
model, and `assets/` all live in the same `outputFolder`.

### Output
One `<section data-start="<startSec>" data-dug="true|false">` **per summary section, in
summary order** — not only dug ones. The companion file is **not required to exist**: with
zero dug sections, every section renders un-dug (skeleton from summary + model).

### Single source of truth
The summary drives structure. Regenerating or retitling the summary automatically
propagates to the dig doc on next render — no reconcile, no drift, no duplication.

---

## 4. Rendering

### Per-section content
| State (`data-dug`) | Renders |
|---|---|
| `false` (un-dug) | numeral ghost · `<h2>` title + `(label)` timestamp link · `dig deeper ▶` trigger · `.gist` (summary `lead` + `bullets`) |
| `true` (dug) | same header, trigger replaced by `show summary ⌃` toggle · **both** `.gist` (lead+bullets, hidden by default) **and** `.dug` (elaboration + slides, shown by default), in the DOM |

Both blocks present in the DOM for dug sections ⇒ "show summary / show dug" is a **zero-fetch
CSS toggle**.

### Top bar
`↑ summary` (same-tab link to the clean summary doc) · `⤢ expand all`.

### #6 — Spacing
Increase inter-section rhythm from today's cramped `1.6em`/`1px` rule to a clearer
separation (target: `section{padding:2.4em 0}` + a `2px` top rule between sections; extra
vertical breathing room around slide `<img>` in dug blocks). Exact values finalized during
implementation against a visual check.

### #3 — Images (base64-inline + missing-asset guard)
Keep inlining each `assets/…jpg` as a base64 data-URI (self-contained, portable HTML). Add
a guard: if a referenced asset is missing on disk, emit a `.missing-slide` placeholder
containing the image's `alt` text instead of throwing — a deleted frame degrades gracefully
rather than 500-ing the whole document. Path-containment check (existing) is retained.

---

## 5. Interaction & Navigation

Because the dig doc renders from summary + model (§3), **all generation moves into the dig
doc**, and the summary side becomes **navigation-only**. This removes the POST→SSE client
and the `target="_blank"` logic from the summary HTML entirely.

### Summary doc — per-section control (same-tab nav)
The summary continues to fetch `dig-state` to label sections; the control becomes a link:
| Section state | Control | Action (same tab) |
|---|---|---|
| un-dug | `dig deeper ▶` | → `…&type=dig-deeper&dig=<startSec>#t=<startSec>` |
| dug | `view detail ↓` | → `…&type=dig-deeper#t=<startSec>` |

### Dig doc — the interactive surface
- **`dig deeper ▶`** (un-dug): POST→SSE generate (existing state machine) → on success inject
  the `.dug` block + slides, flip section to expanded, swap control to `show summary ⌃`.
- **`?dig=<startSec>` on load**: auto-trigger that one section's generation and scroll to it,
  so a single click from the summary lands on the freshly-expanded section. Invalid/absent
  `dig` param ⇒ no-op (render normally).
- **`show summary ⌃` / `show dug ⌄`** (dug): zero-fetch CSS toggle.
- **`⤢ expand all`**: confirm dialog with count + estimate
  (`Expand N remaining sections? ~$X, ~Y min`) → sequential generation with a progress
  indicator (`section k of N…`); already-dug sections skipped.
- **`↑ summary`** (top bar): same-tab link back to the clean summary doc.

### #5 outcome
Every navigation is same-tab. "Back to summary" affordances are (a) the per-section CSS
toggle (inline compare) and (b) the one top-bar link. No tabs are spawned anywhere. The
`target="_blank"` added in `2a3bfc7` is removed from the dig control path.

---

## 6. #1 — Stale Summary HTML (version-gated lazy re-render, rewrite-once)

The summary render output changes (per-section nav controls), so the renderer version is
bumped: `<meta name="generator" content="magazine-skim v1">` → **`magazine-skim v2`**.

On `type=summary` GET in `app/api/html/[id]/route.ts`:
1. Read the cached `htmls/<slug>.html` and extract its embedded generator version.
2. **Current** (`v2`) → serve the cached file as-is (today's fast path, no extra work).
3. **Stale or missing** → re-render fresh from `<base>.md` + `models/<base>.json`,
   **rewrite the cache file**, then serve. Self-heals **once**; the next GET is a cache hit.

Up-to-date docs do **zero** extra work. Only docs whose cache predates the current renderer
re-render, and only on first view. The discipline this requires: **bump the
`magazine-skim vN` string whenever the summary HTML output changes** (an implementation
checklist item).

Tradeoff accepted: a `type=summary` GET may write to disk (cache rewrite) on a stale doc —
acceptable cache-warming for a local single-user tool.

---

## 7. Versioning & Migration

- **Summary:** no batch migration. Fresh-render-on-stale (§6) self-heals every existing
  summary on first view.
- **Dig companion `.md`:** format **unchanged** (delta store). The existing companion docs
  (7 known) render correctly under the new merge renderer with **no migration**.
- **`digVersion`:** bumped only if the generation prompt/output changes during
  implementation; not required by the doc-model redesign alone.

---

## 8. Error Handling

| Failure | Behavior |
|---|---|
| Summary `.md` or model missing when rendering dig doc | Graceful page: "Summary unavailable — regenerate the summary first." No crash. |
| Slide asset missing on disk | `.missing-slide` placeholder with `alt` text (§4) |
| Generation fails (Gemini / yt-dlp / ffmpeg) | Per-section ⚠ error + retry; section stays un-dug; rest of doc unaffected |
| `expand all` — one section fails | Continue remaining; report failed sections at end; never abort the batch |
| Double-trigger same section (`?dig=` + manual click) | Existing job-lock prevents double-spend |
| `?dig=N` with invalid/unknown N | No-op; render normally |

---

## 9. Components & Boundaries

| Unit | Responsibility | Depends on |
|---|---|---|
| `lib/html-doc/render-dig-deeper.ts` (reworked) | Merge summary + model + companion → full-structure HTML; per-section gist/dug blocks; base64 images + missing-asset guard | `parse.ts`, `MagazineModel`, companion parser |
| `lib/dig/companion-doc.ts` (unchanged format) | Delta store of dug sections; upsert | fs atomic write |
| `lib/html-doc/render.ts` (summary) | Per-section control → same-tab nav link (un-dug vs dug); generator version `v2` | `nav.ts` |
| `lib/html-doc/nav.ts` (reworked) | Dig-doc client state machine: in-place expand, show-summary/show-dug toggle, expand-all confirm+progress, `?dig=` auto-trigger; summary-side nav links (no POST) | `dig-state`, dig POST/SSE |
| `app/api/html/[id]/route.ts` (summary path) | Version-gated lazy re-render + rewrite-once | parse + model + render |
| `app/api/videos/[id]/dig/[sectionId]/route.ts` (unchanged) | Per-section generation (Gemini + slides) | existing pipeline |

---

## 10. Testing

Layers per `docs/dev-process.md`. Mock Gemini/yt-dlp/ffmpeg at the lib boundary; E2E mocks
at the API-route level.

### Unit (jest)
- Merge renderer: summary order drives sections; dug overlay on matching `sectionId`;
  un-dug gist from model; mixed dug/un-dug; **zero-dug skeleton**; missing-asset placeholder;
  missing-summary/model graceful path.
- Version-gated re-render: current → cached served unchanged; stale/missing → re-render +
  rewrite; generator-version extraction.
- Expand-all estimate math (count × per-section cost/time).

### Component (RTL)
- Section state machine: un-dug → generating → dug.
- `show summary ⌃` / `show dug ⌄` toggle swaps visible block.
- Expand-all confirm dialog (count/estimate) + progress indicator.

### E2E (Playwright)
- Summary nav → dig doc **same tab** (assert no new tab opened; assert **all** URL params
  per the URL Contracts table; assert scroll to the section).
- `dig deeper ▶` in dig doc → section expands **in place** (no navigation).
- `?dig=N` auto-generation + scroll on load.
- Toggle compare (summary ↔ dug) without refetch.
- `expand all` → confirm → progress → all sections expanded.
- `↑ summary` → same-tab back to summary.
- **#1 regression:** a summary whose cached HTML lacks dig controls serves them after the
  version-gated re-render.
- **Fixtures:** (a) video with mixed dug/un-dug, (b) video with **zero** dug, (c) a
  **missing-asset** case.

---

## 11. URL Contracts

| Component | Link text | Full URL (same tab) |
|---|---|---|
| Summary §, un-dug | `dig deeper ▶` | `/api/html/<videoId>?outputFolder=<of>&type=dig-deeper&dig=<startSec>#t=<startSec>` |
| Summary §, dug | `view detail ↓` | `/api/html/<videoId>?outputFolder=<of>&type=dig-deeper#t=<startSec>` |
| Dig doc top bar | `↑ summary` | `/api/html/<videoId>?outputFolder=<of>&type=summary#t=<startSec?>` |
| Dig §, dug-trigger (client) | `dig deeper ▶` | POST `/api/videos/<videoId>/dig/<startSec>` body `{outputFolder[, force]}` |

## 12. Overlay / Dismissal Contracts

| Component | Mechanism | Expected result |
|---|---|---|
| Expand-all confirm dialog | Confirm button | Begins sequential generation with progress |
| Expand-all confirm dialog | Cancel / backdrop / Escape | Dismiss; no generation; doc unchanged |
| Expand-all progress | Auto-close on completion | Returns to doc; all targeted sections expanded |
| Per-section dug block | `show summary ⌃` / `show dug ⌄` toggle | Swaps visible block (no navigation, no fetch) |

---

## 13. Decided Defaults (were open; locked to keep implementation unblocked)
- **Spacing (#6):** `section{padding:2.4em 0}`, `2px` top rule between sections, `1.2em`
  vertical margin around dug-block slide `<img>`. Adjust only if a Phase-4 visual check
  shows a problem; these are the implementation targets.
- **Expand-all estimate:** fixed heuristic — `remainingCount` × `$0.05` and
  `remainingCount` × `~30s`, rendered as rounded `~$X` / `~Y min`. No live measurement.
- **Summary entry points:** per-section controls **only** (no separate top-level "open
  dig-deeper" link). Matches the existing summary layout; avoids a redundant affordance.

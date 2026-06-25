# Dig-Deeper v2 — In-Place Section Expansion — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Each task follows the project's Per-Task Checklist (docs/dev-process.md): enumerate behaviors → failing tests (RED) → implement (GREEN) → full suite → Claude review → Codex/Claude adversarial review → address → commit. Steps use `- [ ]` syntax.

**Goal:** Make the dig-deeper doc a full mirror of the summary (all sections, gist by default, expandable in place per section), with same-tab navigation, robust section-keying, and a version-gated self-heal for stale summary HTML.

**Architecture:** Approach 1 — the companion `.md` stays a thin delta-store (format unchanged); the dig doc is assembled at render time by a pure **merge** (`dig-merge.ts`) of the parsed summary + model envelope + parsed companion, then rendered to HTML. All generation moves into the dig doc (summary side becomes nav-only). Stale summary HTML self-heals via `reRenderSummaryHtml` gated on a single `GENERATOR_VERSION` constant.

**Tech Stack:** Next.js (app router), TypeScript, markdown-it, Zod, jest+ts-jest (SWC, no typecheck — `tsc --noEmit` is the real gate), @testing-library/react, Playwright.

**Spec:** `docs/superpowers/specs/2026-06-24-dig-deeper-in-place-expansion-design.md` (read §3a, §5, §6 before starting).

## Global Constraints

- **AGENTS.md:** this is a modified Next.js — read `node_modules/next/dist/docs/` before writing route/app code; heed deprecations.
- **TDD:** tests before implementation; must fail first for the right reason. Mock Gemini/yt-dlp/ffmpeg at the lib boundary; E2E mocks at the API-route level.
- **`tsc --noEmit` must pass** before every commit (jest uses SWC and does not typecheck).
- **Full `npm test` green** before every commit (currently 1211 passing — never regress).
- **nav.ts dual-source rule (spec §9):** new dig-doc client logic is authored **inline-only** in `NAV_SCRIPT`, contract-tested by Playwright E2E. Do **not** create a parallel TS copy of new logic. Summary-side edits touch both the TS helper and the inline string (keep in sync).
- **Section-keying contract (spec §3a) is law:** gist by array index (guarded by `sameTitles` vs `envelope.sourceSections`); dug overlay by `startSec` then title fallback; unmatched → visible orphan, never dropped; `timeRange===null` → gist-only/no-dig.
- Commit messages end with the project Co-Authored-By + Claude-Session trailers.

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `lib/html-doc/render.ts` | summary render; owns `GENERATOR_VERSION` | modify |
| `lib/dig/companion-doc.ts` | delta-store; add structured parse | modify (add export) |
| `lib/html-doc/dig-merge.ts` | **pure** §3a merge (no HTML) | **create** |
| `lib/html-doc/rerender.ts` | return rendered html in `rerendered` | modify |
| `app/api/html/[id]/route.ts` | summary version-gate; dig-deeper merge | modify |
| `lib/html-doc/render-dig-deeper.ts` | render MergedSection[] → HTML; asset split | modify (major) |
| `lib/html-doc/nav.ts` | summary nav links; dig-doc inline state machine | modify (major) |
| `tests/lib/html-doc/dig-merge.test.ts` | merge unit tests | create |
| `tests/lib/html-doc/render-dig-deeper.test.ts` | render unit tests | extend |
| `tests/lib/html-doc/rerender.test.ts` | rerender/version tests | extend |
| `tests/e2e/dig-deeper.spec.ts` | E2E contract | extend |

---

## Task 1: GENERATOR_VERSION constant + bump to v2

**Files:**
- Modify: `lib/html-doc/render.ts` (meta line ~104)
- Test: `tests/lib/html-doc/render.test.ts` (or new `generator-version.test.ts`)

**Interfaces:**
- Produces: `export const GENERATOR_VERSION = 'magazine-skim v2';` in `render.ts`.

**Enumerated Behaviors:**
| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | Rendered summary HTML embeds the constant | `renderMagazineHtml(...)` | output contains `<meta name="generator" content="magazine-skim v2">` |
| 2 | Constant is the single source | import | `GENERATOR_VERSION === 'magazine-skim v2'` |

- [ ] Write failing test: render a minimal summary, assert output contains `content="${GENERATOR_VERSION}"` and that `GENERATOR_VERSION` equals `'magazine-skim v2'`.
- [ ] Run → fails (still `v1` / no export).
- [ ] Implement: add `export const GENERATOR_VERSION = 'magazine-skim v2';`; change the meta literal to `content="${GENERATOR_VERSION}"`.
- [ ] Run targeted test → pass. `tsc --noEmit`. Full `npm test`.
- [ ] Commit: `feat(dig): single GENERATOR_VERSION constant, bump magazine-skim v2`.

---

## Task 2: companion-doc — export structured `DugSection[]` parser

**Files:**
- Modify: `lib/dig/companion-doc.ts` (reuse internal frontmatter/sentinel parser; expose a pure function)
- Test: `tests/lib/dig/companion-doc.test.ts`

**Interfaces:**
- Produces: `export function parseDugSections(content: string): DugSection[]` where `DugSection = { sectionId: number; startSec: number; title: string; bodyMarkdown: string; generatedAt: string }` (already defined). Parses sentinel blocks `<!-- dig-section: N -->\n…\n<!-- /dig-section -->`; `bodyMarkdown` excludes the `## title` line; tolerant of `### ` headings inside the body (existing C1 fix).

**Enumerated Behaviors:**
| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | Parses multiple blocks | 3-section companion | 3 DugSections, ids in order |
| 2 | Title from `## ` line | block | `title` = heading text, `bodyMarkdown` excludes it |
| 3 | Body retains `### ` subheadings | block w/ H3 | H3 preserved in bodyMarkdown |
| 4 | No sentinels | summary-like md | `[]` |
| 5 | Malformed/unclosed sentinel | partial | skipped, no throw |

- [ ] Write failing tests for behaviors 1–5 using inline fixture strings (reuse the real companion shape from §7 for one case).
- [ ] Run → fail (no `parseDugSections`).
- [ ] Implement by extracting the existing sentinel/frontmatter logic into `parseDugSections`; have `readDugSectionIds` delegate to it (`.map(s => s.sectionId)`) to keep one parser.
- [ ] Run targeted → pass. `tsc --noEmit`. Full suite.
- [ ] Commit: `feat(dig): parseDugSections structured companion parser`.

---

## Task 3: `dig-merge.ts` — section-keying contract (pure, no HTML)

**Files:**
- Create: `lib/html-doc/dig-merge.ts`
- Test: `tests/lib/html-doc/dig-merge.test.ts`

**Interfaces:**
- Consumes: `ParsedSummary` (`parse.ts`), `ModelEnvelope` (`model-store.ts`), `DugSection[]` (Task 2).
- Produces:
```ts
export interface MergedSection {
  index: number;
  numeral: string | null;
  title: string;
  startSec: number | null;          // null when timeRange absent
  gist: { lead: string; bullets: { text: string }[] } | null;  // null when model missing/drifted
  dug: { bodyMarkdown: string } | null;  // present when matched to a companion section
}
export interface MergeResult { sections: MergedSection[]; orphans: { sectionId: number; title: string; bodyMarkdown: string }[]; }
export function mergeDigDoc(summary: ParsedSummary, envelope: ModelEnvelope | null, dug: DugSection[]): MergeResult;
```

**Keying rules (spec §3a):**
1. Output one `MergedSection` per `summary.sections[i]`, in order.
2. `startSec = section.timeRange?.startSec ?? null`.
3. **Gist:** trusted only if `envelope` non-null AND `sameTitles(summary.sections.map(s=>s.title), envelope.sourceSections)` AND `envelope.model.sections[i]` exists → `{lead, bullets}`; else `gist = null` (skeleton).
4. **Dug match:** for each summary section with `startSec != null`, find a `DugSection` with `sectionId === startSec` → attach. Track consumed dug ids.
5. **Title fallback:** for each not-yet-consumed `DugSection`, match by exact `title` to a not-yet-dug summary section → attach (re-anchor). Track consumed.
6. **Orphans:** any `DugSection` consumed by neither → `orphans[]`.

Reuse/duplicate `sameTitles` (copy the small helper from `rerender.ts`, or export it there and import — prefer exporting `sameTitles` from `rerender.ts` to stay DRY).

**Enumerated Behaviors:**
| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | All summary sections present, in order | 7-section summary, 0 dug | 7 MergedSections, all `dug=null`, gists set |
| 2 | Dug attached by startSec | dug id matches startSec | that section `dug` set, others null |
| 3 | Title fallback re-anchor | dug id≠any startSec but title matches | attached to title-matched section; no orphan |
| 4 | Orphan | dug id & title both absent | in `orphans[]`, not on any section |
| 5 | Timestamp-less section | section timeRange null | `startSec=null`, `dug=null`, gist still set |
| 6 | Model missing | envelope null | all `gist=null`; sections+dug still produced |
| 7 | Model drift (`!sameTitles`) | titles differ | all `gist=null` (skeleton), no wrong gist |
| 8 | Model shorter than summary | model has fewer sections | overflow sections `gist=null` (no crash) |
| 9 | Zero dug, model present | empty companion | gists set, all `dug=null`, no orphans |

- [ ] Write failing tests 1–9 (pure data; no fs). Use small hand-built `ParsedSummary`/`ModelEnvelope`/`DugSection[]` fixtures.
- [ ] Run → fail.
- [ ] Implement `mergeDigDoc` per rules; export `sameTitles` from `rerender.ts` and import it.
- [ ] Run targeted → pass. `tsc --noEmit`. Full suite.
- [ ] (Behaviors adversarial review — >8 behaviors + keying state machine: run a Codex/Claude adversarial pass on the behaviors table before/after implementing.)
- [ ] Commit: `feat(dig): dig-merge keying contract (startSec→title→orphan, model-drift skeleton)`.

---

## Task 4: `rerender.ts` — return rendered html in `rerendered`

**Files:**
- Modify: `lib/html-doc/rerender.ts` (the `rerendered` branch ~`:72`)
- Test: `tests/lib/html-doc/rerender.test.ts`

**Interfaces:**
- Produces: `ReRenderResult` `rerendered` variant becomes `{ status: 'rerendered'; htmlPath: string; html: string }`. The function already computes the html before writing — return it too.

**Enumerated Behaviors:**
| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | rerendered carries html | eligible video | result.html is the same string written to disk |
| 2 | other statuses unchanged | drift/no-model | shape unchanged |

- [ ] Write failing test: stub an eligible video+model; assert `result.status==='rerendered'` and `result.html` contains `GENERATOR_VERSION` and equals the file contents written.
- [ ] Run → fail.
- [ ] Implement: capture the rendered string into a local, write it, return `{status:'rerendered', htmlPath, html}`.
- [ ] Run targeted → pass. `tsc --noEmit`. Full suite (update any existing rerender tests referencing the variant).
- [ ] Commit: `feat(dig): reRenderSummaryHtml returns rendered html string`.

---

## Task 5: Summary route — version-gated re-render + status mapping

**Files:**
- Modify: `app/api/html/[id]/route.ts` (`type === 'summary'` block, lines ~59-68)
- Test: `tests/api/html-route.test.ts` (or the existing route test file)

**Interfaces:**
- Consumes: `GENERATOR_VERSION` (Task 1), `reRenderSummaryHtml` + `ReRenderResult` (Task 4).
- Behavior: read cached `summaryHtml`; extract `<meta name="generator" content="...">`; if `=== GENERATOR_VERSION` serve cached; else call `reRenderSummaryHtml` and map per spec §6 table.

**Status → outcome (spec §6):**
| status | serve |
|---|---|
| (cache version current) | cached file as-is |
| `rerendered` | `result.html` |
| `skipped-not-eligible` | cached as-is |
| `skipped-no-model` / `skipped-no-md` / `skipped-unparseable` / `skipped-drift` | cached (stale) as-is; `console.warn` reason |
| cached read throws (no artifact) | 404 |

**Enumerated Behaviors:**
| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | current version | cache has v2 | served unchanged; `reRenderSummaryHtml` NOT called |
| 2 | stale → rerendered | cache has v1, eligible | served HTML has v2 + dig controls |
| 3 | stale + skipped-drift | cache v1, model drift | served stale cache (still v1); 200; warn logged |
| 4 | stale + skipped-no-model | cache v1, no model | served stale cache; 200 |
| 5 | missing cache file | summaryHtml path gone | 404 |
| 6 | no `summaryHtml` in index | field null | 404 (unchanged) |

- [ ] Write failing tests 1–6 (mock `reRenderSummaryHtml` to return each status; spy that it's not called when current).
- [ ] Run → fail.
- [ ] Implement version extraction (`/content="([^"]*)"/` on the `generator` meta) + the mapping. Reuse the existing `guard()` + `serveHtml()`.
- [ ] Run targeted → pass. `tsc --noEmit`. Full suite.
- [ ] Commit: `fix(dig): version-gated summary re-render self-heals stale dig menu (#1)`.

---

## Task 6: `render-dig-deeper.ts` — render MergedSection[] → HTML

**Files:**
- Modify: `lib/html-doc/render-dig-deeper.ts` (major rework of the body-assembly; keep `buildRenderer`/base64 from Task 7)
- Test: `tests/lib/html-doc/render-dig-deeper.test.ts`

**Interfaces:**
- New signature: `renderDigDeeperHtml(args: { summary: ParsedSummary; envelope: ModelEnvelope | null; dug: DugSection[]; mdPath: string; videoId: string }): string` (route passes inputs; renderer no longer parses the companion itself — it consumes `mergeDigDoc`).
- Emits per `MergedSection`:
  - `<section data-start="<startSec>" data-dug="true|false">` (omit `data-start` when `startSec===null`).
  - `<h2>` title + muted `(label)` ts link (when timeRange) + control: un-dug→`dig deeper ▶` (when startSec!=null); dug→`show summary ⌃` toggle.
  - `.gist` block (lead + `<ul>` bullets) — present whenever `gist!=null`; **hidden by default when `data-dug=true`**, visible when un-dug.
  - `.dug` block (rendered `bodyMarkdown` via the image-aware renderer) — present when `dug!=null`, visible by default.
  - When `gist===null` (skeleton): render title + ts only (no gist block), still attach dig control if startSec!=null.
- Top bar before sections: `<div class="dg-topbar"><a class="dig" data-type="summary">↑ summary</a> <button class="dg-expand-all">⤢ expand all</button></div>`.
- Orphan region after sections (when `orphans.length`): `<section class="dg-orphans"><h2>Unmapped dug sections</h2>` + per orphan: stored title + rendered body + a `<p class="dg-orphan-note">` notice + `<!-- orphan: id -->`.
- **#6 spacing:** `section{padding:2.4em 0}`, `2px` top rule between sections, `1.2em` margin around `.dug img`.

**Enumerated Behaviors:** (assert on HTML string)
| # | Behavior | Expected |
|---|---|---|
| 1 | all summary sections rendered in order | N `<section>` with titles in summary order |
| 2 | un-dug section | `data-dug="false"`, has `.gist`, control text `dig deeper ▶` |
| 3 | dug section | `data-dug="true"`, has both `.gist` (hidden) and `.dug` (visible), control `show summary ⌃` |
| 4 | timestamp-less section | no `data-start`, no dig control, `.gist` shown |
| 5 | skeleton (gist null) | section present, no `.gist`, dig control still present if startSec |
| 6 | orphan region | `Unmapped dug sections` present with orphan body + note |
| 7 | top bar | `↑ summary` + `⤢ expand all` present once |
| 8 | spacing CSS | structural CSS includes `2.4em`/`2px` |

- [ ] Write failing tests 1–8 (call renderer with merged fixtures; pure string assertions).
- [ ] Run → fail.
- [ ] Implement: call `mergeDigDoc`, map sections to HTML, add top bar + orphan region + spacing CSS. Reuse `digControl('summary', …)` for the back-link.
- [ ] Run targeted → pass. `tsc --noEmit`. Full suite.
- [ ] Commit: `feat(dig): merge renderer — full-structure dig doc (gist/dug/orphan/topbar)`.

---

## Task 7: `render-dig-deeper.ts` — split missing-asset guard

**Files:**
- Modify: `lib/html-doc/render-dig-deeper.ts` (`buildRenderer` image rule, lines ~94-113)
- Test: `tests/lib/html-doc/render-dig-deeper.test.ts`

**Behavior (spec §4):**
- Containment violation (`!absPath.startsWith(assetsRoot + sep)`) → `return ''` (silent drop — unchanged).
- Benign missing file (`readFileSync` throws) → `return '<span class="missing-slide">' + esc(altAttr) + '</span>'` (escaped alt; **not** a dropped img).
- Present file → base64 inline (unchanged).

**Enumerated Behaviors:**
| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | present asset | file exists | base64 `<img>` |
| 2 | missing file | file absent | `.missing-slide` with escaped alt; no `<img>` |
| 3 | containment fail | `assets/../..` | `''` (no placeholder, no alt) |
| 4 | alt escaping | alt has `"`/`<` | escaped in placeholder |

- [ ] Write failing tests 1–4.
- [ ] Run → fail.
- [ ] Implement the split (only the two `return ''` branches change; containment branch stays `''`).
- [ ] Run targeted → pass. `tsc --noEmit`. Full suite. Add `.missing-slide` CSS (muted, italic).
- [ ] Commit: `feat(dig): missing-asset placeholder (benign) vs silent containment-drop`.

---

## Task 8: dig-deeper route — load summary+model, containment, merge+render

**Files:**
- Modify: `app/api/html/[id]/route.ts` (`type === 'dig-deeper'` block, lines ~71-83)
- Test: `tests/api/html-route.test.ts`

**Behavior (spec §9):**
- `<base>` = strip `-dig-deeper.md` from `video.digDeeperMd` basename (from the index, not the URL).
- Resolve `summaryMdPath = <dir>/<base>.md`, model via `readModelEnvelope(outputFolder, base)`. `path.resolve` + assert each derived path within `outputFolder` (reuse the `:51` containment pattern); on violation → 400.
- Parse summary (`parseSummaryMarkdown`), parse companion (`parseDugSections`), call `renderDigDeeperHtml({summary, envelope, dug, mdPath, videoId})`.
- The dig doc renders even when the companion has zero dug sections; **also render when `digDeeperMd` is null** by synthesizing an empty `dug=[]` from the summary skeleton (the dig doc is reachable before first dig). *(If `digDeeperMd` null but summary exists → still serve the skeleton.)*
- Summary `.md` missing → graceful "Summary unavailable" page (spec §8).

**Enumerated Behaviors:**
| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | dug + un-dug merged | companion w/ some sections | HTML has all summary sections, dug ones expanded |
| 2 | zero-dug skeleton | empty/absent companion | all sections un-dug, no crash, 200 |
| 3 | summary md missing | `<base>.md` gone | "Summary unavailable" page, 200 (not 500) |
| 4 | model missing | no model json | skeleton-without-gist, 200 |
| 5 | path containment | crafted base with `..` | 400 |
| 6 | orphan companion | dug id absent from summary | orphan region rendered |

- [ ] Write failing tests 1–6 (fs fixtures in a temp dir; or mock fs reads).
- [ ] Run → fail.
- [ ] Implement; reuse `guard`-style containment; call merge+render.
- [ ] Run targeted → pass. `tsc --noEmit`. Full suite.
- [ ] Commit: `feat(dig): dig-deeper route merges summary+model+companion (skeleton-safe)`.

---

## Task 9: `nav.ts` — summary-side controls become same-tab nav links

**Files:**
- Modify: `lib/html-doc/nav.ts` (TS `initDigControls`/`applyDugState` AND the inline `NAV_SCRIPT` summary block)
- Test: `tests/lib/html-doc/nav.test.ts` (jsdom)

**Behavior (spec §5):**
- Summary-side `.dig[data-section]` controls no longer POST. On `dig-state` load:
  - un-dug → `dig deeper ▶`, `href = …&type=dig-deeper&dig=<startSec>#t=<startSec>` (same tab — **no** `target`).
  - dug → `view detail ↓`, `href = …&type=dig-deeper#t=<startSec>` (same tab — **remove** `target="_blank"`/`rel`).
- Remove the POST→SSE `startDig`, `applyLoading/applyError`, force-redig `↻` button from the **summary** path (generation now lives in the dig doc). Keep `parsePageUrl`, `viewDetailHref` (extend to accept the `dig=` variant), `scrollToHashSection`, `wireDigLinks`.
- Update **both** the TS helpers and the inline `NAV_SCRIPT` summary block identically.

**Enumerated Behaviors:**
| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | un-dug control href | dig-state says not dug | href has `type=dig-deeper&dig=<sec>#t=<sec>`, no `target` |
| 2 | dug control href | dig-state says dug | href `type=dig-deeper#t=<sec>`, **no** `target=_blank` |
| 3 | no POST on click | click un-dug | navigates via href (no fetch POST) |
| 4 | dig-state fetch failure | endpoint errors | controls still get nav href (fail-open to un-dug link) |

- [ ] Write failing jsdom tests 1–4 (assert attributes; spy fetch to confirm no POST).
- [ ] Run → fail.
- [ ] Implement in TS helpers; mirror into the inline `NAV_SCRIPT` summary block; delete summary-side POST code in both.
- [ ] Run targeted → pass. `tsc --noEmit`. Full suite (update existing nav tests that asserted POST/`target=_blank`).
- [ ] Commit: `feat(dig): summary dig controls are same-tab nav links (no POST, no new tab) (#5)`.

---

## Task 10: `nav.ts` inline — dig-doc state machine (in-place expand + toggle)

**Files:**
- Modify: `lib/html-doc/nav.ts` (inline `NAV_SCRIPT` — **new dig-doc block, inline-only per §9**)
- Test: `tests/e2e/dig-deeper.spec.ts` (E2E is the contract for inline logic)

**Behavior (spec §5):**
- Detect dig-doc context (URL `type=dig-deeper`). For each `<section data-dug="false">` with a `data-start`, the `dig deeper ▶` control:
  - click → POST `/api/videos/<id>/dig/<startSec>` → EventSource stream → on `done`, **fetch the re-rendered section** (re-GET the dig doc and swap this section's outerHTML, or fetch `dig-state` + reload the section) so the new `.dug` block + slides appear; flip `data-dug="true"`; control becomes `show summary ⌃`. On `error`/transport error → ⚠ retry.
  - Simplest robust approach: on `done`, re-fetch the full dig-deeper HTML, parse it, and replace the current section's node with the matching `[data-start]` node from the fresh doc (preserves base64 slides). Document this in code.
- `show summary ⌃` / `show dug ⌄`: toggle a class on the section that flips `.gist`/`.dug` visibility (CSS); zero fetch.

**Enumerated Behaviors (E2E):**
| # | Behavior | Expected |
|---|---|---|
| 1 | dig in place | click `dig deeper ▶` → section gains `.dug` content + slide img, control → `show summary ⌃`, no navigation |
| 2 | toggle to summary | click `show summary ⌃` → `.gist` visible, `.dug` hidden, control → `show dug ⌄` |
| 3 | toggle back | click `show dug ⌄` → `.dug` visible again |
| 4 | generation error | mocked POST 500 → ⚠ retry, section stays un-dug |

- [ ] Write failing E2E tests 1–4 (mock the dig POST/stream + dig-deeper GET at route level; renderer-driven fixture).
- [ ] Run → fail.
- [ ] Implement inline block + `.gist`/`.dug` toggle CSS in `render-dig-deeper.ts`.
- [ ] Run targeted E2E → pass. `tsc --noEmit`. Full jest suite.
- [ ] Commit: `feat(dig): in-place section expansion + show summary/dug toggle in dig doc`.

---

## Task 11: `nav.ts` inline — guarded `?dig=` auto-trigger + replaceState + pageshow

**Files:**
- Modify: `lib/html-doc/nav.ts` (inline dig-doc block)
- Test: `tests/e2e/dig-deeper.spec.ts`

**Behavior (spec §5):**
- On dig-doc load with `?dig=N`: fetch `dig-state`; if N already dug → **scroll only, no POST**; else trigger Task-10 generation for N once, then scroll. In both cases `history.replaceState` to strip `?dig` (keep `type`, `outputFolder`, `#t`).
- Auto-trigger fires at most once; on failure → ⚠, no auto-retry.
- `pageshow` (`event.persisted`) → re-fetch `dig-state`, re-apply control states (bfcache).

**Enumerated Behaviors (E2E):**
| # | Behavior | Expected |
|---|---|---|
| 1 | `?dig=N` un-dug | generation fires once; section expands; URL no longer has `dig=` |
| 2 | `?dig=N` already-dug | **no POST** (request spy); scrolls; URL stripped |
| 3 | reload after fire | no re-POST (param already stripped) |
| 4 | bfcache restore | navigate away+back → `pageshow` re-fetches dig-state |

- [ ] Write failing E2E 1–4 (request spy to assert POST count).
- [ ] Run → fail.
- [ ] Implement.
- [ ] Run targeted E2E → pass. `tsc --noEmit`. Full jest suite.
- [ ] Commit: `feat(dig): guarded ?dig auto-trigger (already-dug→no POST, replaceState, pageshow)`.

---

## Task 12: `nav.ts` inline — expand-all (confirm + serialized + progress + cancel)

**Files:**
- Modify: `lib/html-doc/nav.ts` (inline dig-doc block) + expand-all UI markup/CSS in `render-dig-deeper.ts`
- Test: `tests/e2e/dig-deeper.spec.ts`

**Behavior (spec §5/§12/§13):**
- `⤢ expand all` → confirm dialog: `Expand N remaining sections? ~$X, ~Y min (rough estimate)` where `N` = un-dug sections with `startSec`, `X = (N*0.05).toFixed(2)`, `Y = Math.ceil(N*30/60)`.
- Confirm → **serialized** loop over remaining sections (skip already-dug/in-progress), each via the Task-10 generate-and-swap; progress `section k of N…`; a **Cancel** stops after the current section completes; failures collected, reported at end; dialog auto-closes on completion.
- Cancel/backdrop/Escape on the confirm dialog → dismiss, no generation.

**Enumerated Behaviors (E2E):**
| # | Behavior | Expected |
|---|---|---|
| 1 | confirm content | dialog shows count + `~$` + `~ min` text |
| 2 | confirm → all expand | all un-dug sections become dug; progress shown |
| 3 | cancel dialog | no generation |
| 4 | cancel mid-batch | stops after current; prior sections persisted/dug |
| 5 | one section fails | batch continues; failure reported at end |

- [ ] Write failing E2E 1–5 (mock per-section POST; make one 500 for #5).
- [ ] Run → fail.
- [ ] Implement dialog + loop + cancel + estimate.
- [ ] Run targeted E2E → pass. `tsc --noEmit`. Full jest suite.
- [ ] Commit: `feat(dig): expand-all with confirm/estimate, serialized progress, cancel`.

---

## Task 13: E2E suite + fixtures (regression + coverage)

**Files:**
- Modify: `tests/e2e/dig-deeper.spec.ts`; fixtures under `tests/e2e/fixtures/` (or existing renderer-driven setup)

**Coverage (spec §10):**
- Summary nav → dig doc **same tab** (no new tab; assert **all** URL params; scroll).
- `↑ summary` same-tab back (no `#t`).
- `#1 regression`: a summary cached at `v1` serves dig controls after version-gated re-render.
- Fixtures: (a) mixed dug/un-dug, (b) zero dug, (c) missing-asset, (d) **real existing companion shape** (§7), (e) **orphan** companion section.

**Enumerated Behaviors (E2E):**
| # | Behavior | Expected |
|---|---|---|
| 1 | same-tab nav | clicking `dig deeper ▶` on summary opens dig doc in same tab (page count unchanged), correct params, scrolled |
| 2 | ↑ summary | returns to summary, same tab, no `#t` |
| 3 | v1 regression | stale summary → dig controls appear |
| 4 | orphan fixture | "Unmapped dug sections" visible |
| 5 | missing-asset fixture | `.missing-slide` placeholder visible |

- [ ] Write failing E2E 1–5 + fixtures.
- [ ] Run → fail.
- [ ] Wire fixtures; implement any small gaps surfaced.
- [ ] Run full E2E → pass. `tsc --noEmit`. Full jest suite.
- [ ] Commit: `test(dig): E2E coverage — same-tab nav, v1 regression, orphan, missing-asset`.

---

## Self-Review (author checklist — completed)

- **Spec coverage:** §3a→T3; §4 images→T7, spacing→T6; §5 summary-nav→T9, in-place+toggle→T10, ?dig+bfcache→T11, expand-all→T12; §6→T1/T4/T5; §7 verify→done in spec, fixture→T13; §8 error rows→T3/T5/T6/T7/T8/T10/T11/T12; §9 boundaries→all; §10 tests→each task + T13; §11 URL contracts→T9/T6; §12 dismissal→T12.
- **Placeholder scan:** none (estimate formula, version string, signatures all concrete).
- **Type consistency:** `MergedSection`/`MergeResult`/`mergeDigDoc` (T3) consumed by T6/T8; `DugSection` (T2) by T3/T8; `GENERATOR_VERSION` (T1) by T4/T5; `reRenderSummaryHtml` `{html}` (T4) by T5; `renderDigDeeperHtml({...})` new arg object (T6) called by T8.
- **Ordering:** T1→T2→T3→T4→T5 (backend self-heal + merge core), T6→T7→T8 (render+route), T9→T12 (client), T13 (E2E). Each independently testable.

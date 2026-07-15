# Cloud Dig-Deeper Frontend — Design Spec

**Date:** 2026-07-14
**Status:** Approved (brainstorming gate)
**Predecessors:**
- `2026-07-12-cloud-dig-generation-design.md` (PR #15 — cloud dig **generation** backend; the cloud-aware `POST /dig/[sectionId]` trigger).
- `2026-07-14-cloud-dig-serving-design.md` (PR #19 — cloud dig **serving**: the read-only `type=dig-deeper` doc + `dig-state` endpoint). This slice implements deferral **§14.3** of the generation spec: the frontend affordance that makes the serve slice reachable and the trigger usable.

---

## 1. Goal

Make cloud "Dig deeper" **usable from the UI**. Today every server piece exists (read-only dig doc, `dig-state`, cloud-aware POST trigger) but nothing in the cloud UI reaches them. This slice adds the frontend so a signed-in cloud user can, from the cloud app:

1. Open the merged skim+dig doc for a video, and
2. Trigger a per-section dig and watch it complete in place — the same interaction the **local** app already offers, adapted to the cloud's poll-based (non-SSE) progress model.

This is a **frontend-only** slice. The generation and serving backends are done and unchanged. The one non-frontend change is re-enabling interactivity in the *already-shared* dig-doc renderer for the cloud path.

---

## 2. Background — what already exists (all cloud-aware, all built)

| Piece | Contract | Notes |
|---|---|---|
| Dig serve | `GET /api/html/<videoId>?playlist=<uuid>&type=dig-deeper` | Auth required. Returns the merged skim+dig HTML doc. **Today rendered `readOnly: true`** — triggers + JS engine stripped. `format` must be `html` or absent; `download=1` optional. |
| dig-state | `GET /api/videos/<videoId>/dig-state?playlist=<uuid>` | Auth required. Returns `{ sectionIds: number[] }` (ascending; each id `== section.timeRange.startSec`). Blob-presence based, cheap — **designed to be polled**. |
| Dig trigger | `POST /api/videos/<videoId>/dig/<sectionId>?playlist=<uuid>` | Auth **and a registered account** required (anonymous → `403`). **No request body** in cloud mode. Responses in §7. |

**Two forced constraints (not design choices — the code dictates them):**

1. **Progress must be poll-based.** The local SSE stream (`app/api/videos/[id]/dig/[sectionId]/stream/route.ts`) is backed by an **in-memory single-process job registry** (`lib/job-registry.ts`) with no Supabase branch. Cloud digs run on a **separate worker**, so that stream returns `404 job not found` for a cloud job id. Cloud progress therefore polls `dig-state`, reusing the established `pollUntilTerminal` idiom (`lib/job-queue/poll-client.ts`, already used by `components/cloud/IngestProgressBanner.tsx`).
2. **The local dig UX is server-rendered HTML, not React.** The entire trigger/expand/swap experience is inlined vanilla-JS (`lib/html-doc/nav.ts` `NAV_SCRIPT`) inside the doc emitted by `lib/html-doc/render-dig-deeper.ts`. The cloud serve renders that same doc with `readOnly: true`, which omits the per-section `dig-trigger` markup **and** the whole `navScript` engine. Re-enabling cloud interactivity therefore happens **in the doc**, not in a React component.

---

## 3. Design decisions (resolved at brainstorming gate)

| # | Fork | Decision | Rationale |
|---|---|---|---|
| D1 | Where the trigger lives / granularity | **Interactive dig doc, mirroring local** — per-section triggers inside the served doc; React only provides the menu doorway. | Matches the reference UX the user knows; per-section = natural cost granularity; reuses the `dig-trigger` markup that already exists in the renderer; no new section data needs to reach React. |
| D2 | Cost confirmation before a dig | **No confirm — frictionless, like local.** | Per-section cost is small and bounded (~23¢); the backend already enforces per-user quota + daily caps (`429`/`503`); the button's in-flight state prevents double-fire. |
| D3 | Anonymous users | **Pre-disable the trigger** (tooltip: "Create an account to dig deeper") **and keep the `403` handler as the server-enforced fallback.** | Honest affordance (the button matches what it can do); matches the existing cloud-menu disabled pattern (`summaryReady` false → `aria-disabled` + tooltip); the `403` path is required regardless (defense-in-depth + status-change race), so pre-disable is a strict addition on top of it. |
| D4 | Batch "expand all" | **Excluded from MVP.** | One click would enqueue every un-dug section at ~23¢ each — a cost cliff at odds with D2's frictionless-but-bounded posture. Per-section only. |

---

## 4. Async-operation classification (dev-process requirement)

- **Blocking or non-blocking?** **Non-blocking.** A dig runs on the worker; the user can keep reading other sections, open other sections' digs, or leave the tab. No full-screen overlay. The only blocked element is the one section's trigger, which shows its own in-flight state.
- **What the user sees / does while it runs:** the clicked section's trigger becomes `⏳ generating…` (disabled); everything else on the page stays live. The client polls `dig-state` in the background.
- **What triggers dismissal:** there is no modal to dismiss. The in-flight state **auto-resolves** to the dug section (on completion) or to an inline `⚠ retry` (on error/timeout). See §7.

---

## 5. URL Contracts (dev-process requirement)

| Component | Link text / trigger | Full URL (all params) |
|---|---|---|
| `VideoMenu` (cloud) | `Dig deeper ↗` (click) | `GET /api/html/<videoId>?playlist=<uuid>&type=dig-deeper` — opened in a new tab (`target="_blank" rel="noopener noreferrer"`) |
| In-doc per-section trigger | `dig deeper ▶` (click) | `POST /api/videos/<videoId>/dig/<sectionId>?playlist=<uuid>` — **no body** |
| In-doc poll (after `202`) | automatic | `GET /api/videos/<videoId>/dig-state?playlist=<uuid>` |
| In-doc re-fetch on completion | automatic | `GET location.href` (the dig-deeper doc URL itself) |

`digHref(playlistId, videoId)` (new, `lib/client/api.ts`) builds the menu URL — mirrors the existing `summaryHref`, setting `playlist` + `type=dig-deeper` (no `outputFolder`, per the cloud contract).

---

## 6. Overlay / dismissal (dev-process requirement)

There is **no modal or overlay** in this slice (no confirm dialog per D2, no expand-all dialog per D4). The only stateful surface is the per-section trigger. Its states and how each is left:

| Component | State | Mechanism → expected result |
|---|---|---|
| Per-section trigger | idle | `dig deeper ▶` — clickable |
| Per-section trigger | in-flight | `⏳ generating…`, disabled — **auto**-transitions to dug or error; not user-dismissable |
| Per-section trigger | done | replaced by dug section body + `show summary ⌃` toggle (pure CSS toggle, zero fetch) |
| Per-section trigger | error | `⚠ retry` — **click** re-POSTs (same path) |
| Per-section trigger (anonymous) | disabled | `aria-disabled`, tooltip "Create an account to dig deeper" — not clickable |

---

## 7. Interactive doc mechanics

### 7.1 Render mode
`app/api/html/[id]/route.ts` cloud `dig-deeper` branch stops passing `readOnly: true` and instead requests a **cloud-interactive** render:

- The per-section `dig-trigger` markup (already present in `render-dig-deeper.ts`, gated by `!readOnly`) is emitted for un-dug sections.
- A **separate** nonced inline script (`digCloudScript`) is injected **in place of** the local `navScript` (see 7.2 for why a separate script rather than a branch inside `NAV_SCRIPT`).
- The script derives what it needs from the page URL itself — `videoId` from the path, `playlistId` from the `?playlist=` query (already on the dig-doc URL) — so no extra data attributes are required. Its mere presence signals cloud mode (it is injected only in cloud renders).
- **`isAnonymous`** is resolved at the serve route from **`profiles.is_anonymous`, fail-closed** — the SAME source and semantics the cloud dig POST route uses (`dig/[sectionId]/route.ts:47-61`); `user.is_anonymous` is explicitly not trusted in this project. It is threaded into the render so anonymous users get the pre-disabled trigger (D3).

**Shared-code invariant (carried from PR #19):** with the cloud flag **off** (i.e. the local path and every existing caller), `render-dig-deeper.ts` and `nav.ts` output must remain **byte-identical** to today. The new mode is strictly additive and off by default.

### 7.2 Poll-based trigger handler
The `navScript` trigger handler gets a **cloud branch** that reuses the existing DOM-swap logic and forks only the completion-wait (SSE → poll):

1. Click `dig deeper ▶` → set `⏳ generating…`, disable, `POST /api/videos/<videoId>/dig/<sectionId>?playlist=<uuid>` (no body).
2. On `202 {status:'enqueued', jobId}` → **poll** `GET /dig-state?playlist=<uuid>` with 2s→10s backoff until `sectionId ∈ sectionIds`.
3. Section appears → re-fetch `location.href`, parse, swap the `[data-start="<sectionId>"]` `<section>` node in place (identical to the local `done` handler).
4. On `200 {status:'ready'}` (race — already dug) → skip polling, re-fetch + swap immediately.
5. On any error response or a poll timeout (~3 min ceiling) → set `⚠ retry` (see §7.3).

Same-origin `fetch`/`POST` carry the Supabase auth cookie, so no token plumbing is needed in the doc.

**Why a separate `digCloudScript`, not a branch inside `NAV_SCRIPT`:** `NAV_SCRIPT` is one shared inline-string constant used by the local path. Adding a cloud branch inside it would change the local output and **break the byte-identical-when-off invariant** (§7.1) — the load-bearing constraint carried from PR #19. So cloud gets a *separate* nonced script injected in place of `navScript`; `NAV_SCRIPT` is left untouched. The cost is some duplication of the DOM-swap logic; it is mitigated by (a) exported, jsdom-tested TS mirror helpers (`swapDugSection`/`pollUntilDug`/`startCloudDig`), (b) a test that **executes the shipped inline string** in jsdom, and (c) a `DRIFT WARNING` comment — the same pattern the repo already uses for `NAV_SCRIPT`.

### 7.3 Error map
| Response / condition | Trigger UI | Wording note |
|---|---|---|
| `202 enqueued` | `⏳ generating…` then poll | — |
| `200 ready` | swap immediately | race with another tab / prior dig |
| `403` (anonymous) | `⚠ Create an account to dig deeper` | server-enforced fallback under the pre-disabled UI (D3) |
| `404 section not found` | `⚠ retry` | should not occur — section id came from the rendered doc |
| `409 repair needed` | `⚠ retry` | blob lost after a completed row |
| `429` (rate / quota) | `⚠ busy — try later` | server sends `Retry-After: 60` |
| `503` (capacity / daily cap) | `⚠ busy — try later` | — |
| network error / poll timeout | `⚠ retry` | timeout ceiling ~3 min so a stuck worker doesn't poll forever |

Poll failure mode: `dig-state` reports presence only, so an *explicitly failed* worker job never appears — the timeout ceiling is what converts "never appears" into a user-visible `⚠ retry`. (Polling the job-status API for precise failure is a possible future refinement, out of scope here.)

---

## 8. Menu affordance
`components/VideoMenu.tsx`, cloud block: add a `Dig deeper ↗` item, gated on `video.summaryReady === true` exactly like `View summary ↗` (disabled `aria-disabled` span with a "Finalizing…" tooltip when not ready). Enabled even when zero sections are dug — the user opens the doc *to start* digging. Href from `digHref(pid, video.id)`, `target="_blank" rel="noopener noreferrer"`, closes the menu on click.

---

## 9. Enumerated behaviors (contract for the plan's tests)

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | `digHref` builds cloud dig URL | `digHref(pid, vid)` | `/api/html/<vid>?playlist=<pid>&type=dig-deeper` (no `outputFolder`, no `format`) |
| 2 | Menu shows enabled Dig-deeper when ready | cloud row, `summaryReady===true` | `<a href={digHref…} target="_blank">Dig deeper ↗</a>` |
| 3 | Menu shows disabled Dig-deeper when not ready | cloud row, `summaryReady!==true` | `aria-disabled` span, "Finalizing…" tooltip, no href |
| 4 | Menu hides Dig-deeper in local mode | local scope | item absent (`cloudMode` gate) |
| 5 | Serve renders interactive (not readOnly) for cloud dig | `type=dig-deeper` cloud GET | `dig-trigger` markup present for un-dug sections; `navScript` injected; `playlist` + cloud flag embedded |
| 6 | Serve keeps local/off path byte-identical | any non-cloud caller of `renderDigDeeperDoc` | output byte-identical to pre-slice (readOnly + all existing callers unchanged) |
| 7 | Anonymous user gets pre-disabled trigger | cloud dig GET, `isAnonymous` | trigger rendered `aria-disabled` + tooltip; no POST fires on click |
| 8 | Trigger happy path | click `dig deeper ▶`, `202` then section appears | `⏳ generating…` → poll dig-state → re-fetch → section swapped to dug |
| 9 | Trigger already-dug race | click, `200 ready` | swap immediately, no poll |
| 10 | Trigger 403 fallback | click, `403` | `⚠ Create an account to dig deeper`, no swap |
| 11 | Trigger 429/503 | click, `429`/`503` | `⚠ busy — try later` |
| 12 | Trigger 409 / 404 / network | click, error | `⚠ retry`; clicking retry re-POSTs |
| 13 | Poll timeout | `202` then section never appears within ceiling | `⚠ retry` (poll stops) |
| 14 | Retry after error | click `⚠ retry` | re-POST from idle semantics |
| 15 | Show-summary toggle on a dug section | click `show summary ⌃` | pure CSS class toggle, zero fetch |

---

## 10. Testing strategy

- **`digHref`** — unit test (assert every param).
- **`VideoMenu` cloud mode** — component test: enabled link when `summaryReady`, disabled span when not, absent in local scope (behaviors 2–4).
- **Poll trigger handler** — jsdom tests against the `nav.ts` exported mirror helpers: mock `fetch` for `202`→poll→`done` swap, `200` immediate swap, `403`, `429/503`, timeout, retry (behaviors 8–14).
- **Render mode** — `render-dig-deeper` tests: cloud flag on → triggers + navScript + playlist/mode markers present; cloud flag off → **byte-identical** to current output; anonymous → pre-disabled trigger (behaviors 5–7).
- **Serve integration** — real local Supabase: open `type=dig-deeper` for a promoted video, assert the doc is interactive (trigger markup + nonced navScript + `playlist` embedded) and CSP is nonce-based. (This also finally gives the serve path a committed integration test, which PR #19 noted was missing.)
- **No live Gemini / no charge** — the serve + poll paths must not touch generation or `reserve_serve_model`; assert `spend_ledger` unchanged across a serve (the money invariant from the serving slice still holds — viewing/opening the doc is free; only the POST trigger spends, and that's the already-built, already-tested backend).

Mock boundaries per project policy: mock Supabase auth/`createServerSupabase` at the route boundary; mock `fetch` in jsdom handler tests.

---

## 11. Files touched

| File | Change | Shared? |
|---|---|---|
| `lib/client/api.ts` | add `digHref` | no |
| `components/VideoMenu.tsx` | add cloud `Dig deeper ↗` item | no |
| `app/api/html/[id]/route.ts` | cloud `dig-deeper` branch: interactive render (not `readOnly`), inject `playlist` + cloud flag, thread `isAnonymous` | no |
| `lib/html-doc/render-dig-deeper.ts` | add cloud-interactive mode (additive; off = byte-identical); pre-disabled trigger for anonymous | **yes → mandatory dual re-review** |
| `lib/html-doc/nav.ts` | add poll branch to trigger handler (SSE-vs-poll fork); reuse DOM-swap | **yes → mandatory dual re-review** |

**Re-review trigger (dev-process):** the two `lib/html-doc/*` files are shared with the already-merged local path. Per the Iterative Re-Review policy this slice **requires** dual adversarial review to convergence, with explicit verification that (a) the off/local path is byte-identical, and (b) the money invariant is untouched (serving/opening never charges).

---

## 12. Out of scope (noted for later)

- **Expand-all** batch dig (D4).
- **Summary-doc deep-links** — the cloud summary doc staying read-only means no per-section `dig deeper` links there and no `?dig=N` auto-trigger; entry is the menu only.
- **Force-refresh** of a dug section — the cloud POST has no `force`, and `loadDigForServe` lists **only current-version** dig blobs, so a cloud dug section is always current: no `↻ outdated` / `dig-refresh` control is emitted in cloud (that affordance stays local-only, where the local generator can be behind). An older-version dig simply does not appear as dug in cloud, so its section renders an ordinary `dig deeper ▶` trigger and re-digs at the current version. The render explicitly suppresses `dig-refresh` when the `cloud` flag is set, so no dead control can appear even if a stale blob somehow surfaced.
- **Precise job-failure signal** — polling the job-status API for explicit worker failure (vs. the timeout ceiling used here).

# Share pre-warm (backlog #14) — implementation plan

**Goal:** A freshly-minted share link serves immediately instead of returning 503 "not ready".

**Approach:** When a share token is created, warm the owner's rendered "magazine" model by hitting
the SAME owner-charged serve path a normal HTML view uses (`summaryHref` → `GET /api/html/<videoId>?
playlist=<pid>&type=summary`). That path generates+stores the model when absent and is a cheap no-op
read when it already exists (idempotent). Reveal the link only after the warm attempt so the user
cannot copy a not-yet-ready link. **No new server-side money-path code** — reuses the reviewed owner
serve endpoint (`resolveMagazineModel`/`reserve_serve_model`); the anon share-read route stays a pure
generate-free leaf.

**Why client-side (not server-side in `/api/share`):** keeps `/api/share` a thin, never-charges-Gemini
route; reuses the existing reviewed serve orchestration instead of duplicating it; and the owner's
browser doing exactly what "view the doc" does is the least-surprising trigger.

## Global constraints
- Warming is **best-effort**: never throws, never redirects, and is **time-bounded**
  (`WARM_MODEL_TIMEOUT_MS`, 15s) so a stalled request can't freeze the dialog. If it fails (serve
  budget exhausted, transient 5xx, expired session, timeout), reveal the link anyway — it heals on the
  owner's next view.
- **Spend is unchanged from a normal owner view:** a FRESH model is read without charging; an
  absent/stale model is generated, bounded by `reserve_serve_model` (per owner/doc/day lease + K
  attempt cap). No new charge, no double-charge, no budget bypass — warming just triggers the same
  reviewed serve path at a new moment.

## Enumerated Behaviors

### `warmSummaryModel(playlistId, videoId)` — `lib/client/api.ts`
| # | Behavior | Trigger | Expected |
|---|---|---|---|
| W1 | Warms via the owner serve URL | called | `fetch(summaryHref(playlistId, videoId))` = `/api/html/<videoId>?playlist=<pid>&type=summary` (no `download`, no `format`) |
| W2 | Success | `res.ok === true` | resolves `true` |
| W3 | Non-ok response is swallowed | `res.ok === false` (503/402/500/401) | resolves `false`, does **not** throw, does **not** redirect |
| W4 | Network error is swallowed | `fetch` rejects | resolves `false`, does **not** throw |

### `ShareDialog` — `components/cloud/ShareDialog.tsx`
| # | Behavior | Trigger | Expected |
|---|---|---|---|
| S1 | Warm before reveal | Create succeeds | `warmSummaryModel(playlistId, videoId)` called; link revealed **only after** the warm promise settles (button stays "Working…" meanwhile) |
| S2 | Warm failure still reveals | warm resolves `false` | link `/s/<token>` shown; **no** `role=alert` |
| S3 | Create failure → no warm | `createShare` rejects | `warmSummaryModel` **not** called; error/redirect path unchanged |
| S4 | In-flight guard covers the whole op | double-click Create | `createShare` fires once (existing guard, unchanged) |

**Mutation checks:**
- Remove the `await warmSummaryModel(...)` call → S1 goes red (warm not called).
- Reveal before awaiting warm (drop the `await`) → S1's "revealed only after warm settles" (deferred-promise) assertion goes red.
- Remove the `try/catch` in `warmSummaryModel` → W3/W4 go red (throws instead of resolving `false`).

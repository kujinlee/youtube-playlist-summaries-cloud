# Adversarial Plan Review — Stage 1F-a (Authorized Doc Serving)

**Artifact:** `docs/superpowers/plans/2026-07-09-stage-1f-a-authorized-doc-serving.md`
**Contract:** `docs/superpowers/specs/2026-07-09-stage-1f-a-authorized-doc-serving-design.md`
**Reviewer:** Claude (independent pass, alongside a real Codex pass)
**Date:** 2026-07-09
**Verdict:** **NOT ready to execute** — 1 Blocking, 2 High. Revise Tasks 5, 2, 7 before dispatch.

This pass verified every cited signature/line against the real code. The **money path (Task 1
reserve RPC) is SOUND** — the defects are in the shared-render refactor (Task 5), a shared-schema
change (Task 2), and real-DB test fidelity (Task 7).

---

## BLOCKING

### B-1 — Task 5 breaks `render-dig-deeper.ts` (compile break + print regression). CORRECTNESS
**Where:** Task 5 Steps 4/5/6 (theme.ts / nav.ts / render.ts), modified-files list.

**Defect.** Task 5 converts the exported **consts** `THEME_HEAD_SCRIPT`, `PRINT_BUTTON`,
`THEME_TOGGLE_SCRIPT` (theme.ts) and `NAV_SCRIPT` (nav.ts) into **functions** and removes the const
exports. But those exact symbols are imported by a **second consumer the plan never touches** —
`lib/html-doc/render-dig-deeper.ts`:

```
render-dig-deeper.ts:6   themeStyleBlock, THEME_HEAD_SCRIPT, THEME_TOGGLE_BUTTON, THEME_TOGGLE_SCRIPT, PRINT_BUTTON,
render-dig-deeper.ts:10  import { digControl, NAV_SCRIPT, NAV_CSS } from './nav';
render-dig-deeper.ts:468 ${THEME_HEAD_SCRIPT}
render-dig-deeper.ts:474 ${THEME_TOGGLE_BUTTON}${PRINT_BUTTON}
render-dig-deeper.ts:479 ${NAV_SCRIPT}${THEME_TOGGLE_SCRIPT}${zoomScript}...
```

**Two failures:**
1. **Compile break.** Removing the const exports → `TS2305 "Module has no exported member
   THEME_HEAD_SCRIPT/PRINT_BUTTON/THEME_TOGGLE_SCRIPT/NAV_SCRIPT"` in `render-dig-deeper.ts`. Task 5
   **cannot `tsc` at its own commit point** (violates dev-process "every task compiles at its commit").
   Task 5 Step 7 runs only `npx jest render-nonce html-doc render theme nav` — it does not typecheck or
   run the dig-deeper renderer, so the break slips to Task 9 `tsc`/`npm test`.
2. **Behavioral regression (even after fixing imports).** D11 removes the inline `onclick` from the
   print button for **both** render paths, wiring `printListenerScript()` only into `render.ts`. If
   `render-dig-deeper.ts` is updated to call `printButton()` but not also emit `printListenerScript()`,
   the **local dig-deeper doc's print button silently stops working** — a B21 (local behavior-parity)
   violation on the dig-deeper artifact.

**Why it matters.** Task 5 is explicitly the "refactor of already-merged shared code" re-review
trigger (§8). The plan's own File-Structure list and Self-Review §3 ("Type consistency … No
signature/name drift found") both missed the second shared consumer — exactly the class of defect the
re-review gate exists to catch.

**Fix.** Add `lib/html-doc/render-dig-deeper.ts` to Task 5's modified files, its jest command, and its
re-review scope. Update it to call `themeHeadScript()`, `printButton()` **+ `printListenerScript()`**,
`themeToggleScript()`, `navScript()` — all with **no nonce arg** (local dig path is CSP-free), so
output stays behavior-identical AND the print button keeps working. Task 5 Step 7 must run
`npx jest render-dig-deeper` and a `tsc --noEmit` before commit.

---

## HIGH

### H-1 — Task 2 `maxItems: 20` on the SHARED schema changes LOCAL behavior + bricks >20-section docs. CORRECTNESS
**Where:** Task 2 Step 4 — adds `maxItems: 20` to `MAGAZINE_RESPONSE_SCHEMA.properties.sections`.

**Defect.** `MAGAZINE_RESPONSE_SCHEMA` is a **shared const** used by the *same* `generateMagazineModel`
that the **local** `generate.ts:39` (`runHtmlDoc`) calls. Today it has `minItems: 1` and **no
maxItems** (verified, gemini.ts:164-166) — unbounded. Adding `maxItems: 20` interacts with the existing
hard check `if (parsed.sections.length !== sections.length) throw 'section count mismatch'`
(gemini.ts:497): for any summary with **>20 sections**, controlled generation caps the model at 20
sections → count mismatch → throw. Consequences:
- **Local regression:** Task 2 asserts "the local `generateMagazineModel(sections, language)` caller
  keeps working unchanged," but a >20-section local doc that renders fine today would now **fail
  materialization**. This is a shared-code behavior change the plan denies making.
- **Cloud permanent-failure:** in cloud, such a doc can never materialize → every view reserves →
  charges → generates → throws → lease expires → reclaims, until `K` is burned → **503 forever** (a
  self-inflicted, paid, permanent brick for long videos).

**Why it matters.** The spec's `maxItems` requirement (§4.2) is a *cost* bound; the real output bound is
`maxOutputTokens`. A too-tight structural cap on a shared schema silently narrows the input domain of an
already-shipped local function.

**Fix.** Pick generous headroom (e.g. `maxItems: 60`) so realistic section counts never trip the
equality check, OR relax the strict `!==` check to `>`, AND update Task 2's "local unchanged" claim to
acknowledge the shared-schema change. Add a test with a >20-section input asserting the chosen behavior.

### H-2 — Task 7 Step 7 isolation test is underspecified AND its seed omits fields the real route reads. CORRECTNESS
**Where:** Task 7 Step 7 (real-DB isolation test) + the `seed()`/`seedPromotedDoc()` helpers (Tasks 6/1).

**Defect.** The only **real-DB** coverage of the route happy path is the isolation test, whose body is a
**comment, not code** ("Anon owner viewing its OWN doc → 200 path"). Worse, the integration seed helpers
write `data: { id, artifacts: { summaryMd: { key, status: 'promoted' } } }` with **no top-level
`summaryMd`, no `language`, no `docVersion`**. But the real route reads the MD key from
`video.summaryMd` (top-level) and passes `video.language` to `resolveMagazineModel`. The real cloud
worker DOES set both (summary-handler.ts:157 `summaryMd: \`${baseName}.md\``, and `language` via the
`geminiFields` spread) — the **seed helper does not**. So a real-DB drive of the own-doc path would hit
`if (!mdKey) return 404` → the "own doc → 200" assertion **cannot pass as written**. The route-level
test (Step 1) only passes because its mock's `promotedVideo` manually injects `summaryMd`.

**Why it matters.** The mocked route test and the (only) real-DB test disagree about the video shape.
The mock hides the field the real path depends on, so a genuine RLS/own-doc 200 is never actually
exercised end-to-end. This is precisely the "test would pass but production 404s the happy path" class.

**Fix.** (a) Write the Step-7 test as real code, not a comment. (b) Give the integration seed helpers the
**real worker's data shape** — top-level `summaryMd: \`${videoId}.md\``, `language: 'en'`,
`docVersion`, plus a matching MD blob uploaded to `{owner}/{playlist_key}/{videoId}.md` — so the own-doc
path returns 200 and the foreign-owner path 404 against real RLS.

---

## MEDIUM

### M-1 — Task 7 whole-file route rewrite doesn't reference the existing local-path test. CORRECTNESS
`tests/api/html-serve.test.ts` exercises the current (local) route. Task 7 rewrites the whole file into
`serveCloud`/`serveLocal` and adds a new `if (searchParams.get('playlist')) return 400` to the local
branch, but never names that test for re-run/update. Step 5's command is only `npx jest
html-serve-cloud`; a local-path regression is caught only at Task 9's full suite. **Fix:** add
`html-serve` to Task 7's test command and note any expected assertion updates.

### M-2 — Task 7 Step 6 mischaracterizes the confinement mechanism. INTENT/DESIGN
`scripts/check-service-confinement.ts` does a **reachability analysis to `lib/supabase/service.ts` from
entrypoints** (TARGET = `lib/supabase/service.ts`), not a per-file "`createServiceClient` is never
imported" grep as Step 6 states. `app/api/**/route.ts` is already an entrypoint pattern, so the serve
route may already be scanned; "append to the allowlist" is the wrong verb (a *violation* there means
service.ts is reachable → the script FAILs). **Fix:** restate Step 6 in terms of the real script — verify
the serve route does not transitively reach `service.ts` (it imports `getStorageBundle`/
`getPrincipalFromSession`/`resolveOwnedPlaylistKey`, none of which import `service.ts`) and that the run
prints "service_role confinement OK." This satisfies B20 without the inaccurate assertion.

### M-3 — Task 2 error wrapping drops the `NonRetryableError` identity of the input-cap throw. CORRECTNESS
`generateMagazineModel`'s catch re-wraps everything except `AbortError` into a generic `Error`, so the
`assertMagazineInputWithinCap` `NonRetryableError` loses its type (the transcribe-side precedent
preserves it as a distinct site). Harmless on the serve path (no retry runner), but inconsistent and it
weakens any future caller that classifies on error type. **Fix:** rethrow `NonRetryableError` unwrapped
alongside `AbortError`.

---

## LOW / NITS

- **L-1 (Task 6):** A *successful* materialize never releases its lease; the marker row persists with a
  live `lease_expires_at` for `LEASE_TTL`. A drift or `generatorVersion` change re-viewed **within** that
  window returns 503 `busy` (reserve → `in_flight`, cached env not fresh) instead of regenerating —
  self-heals after TTL. The drift test masks this by manually `delete()`-ing the marker. Acceptable, but
  document it (rare: the common non-drift re-view hits the `isFresh` fast path and never reserves).
- **L-2 (Task 3):** The rerender.ts Step-4 edit recomputes `getPrincipal(outputFolder)` although
  `principal` is already in scope at rerender.ts:34 — reuse the existing variable.
- **L-3 (Task 1):** The `v_claimed = 0 → SELECT attempt_count` branch relies on ON-CONFLICT row-lock
  serialization for the concurrent-reclaim race; correct (both `in_flight` and `attempts_exhausted`
  outcomes are non-charging), but worth a one-line comment so a future editor doesn't "optimize" the
  lock away.

---

## Verified SOUND (no action — recorded so the convergence trail shows what was checked)

**Money path (Task 1) — traced against 0011 patterns and the §4.2 contract:**
- **Exactly K charges.** The K-loop test nets `reserved_cents = 30 = 5·6`; attempt_count increments
  1→5 under `attempt_count < K`, the 6th reclaim fails the `WHERE` → `v_claimed=0` → `attempts_exhausted`.
  No K±1.
- **at_capacity rolls back the claim, not into a brick.** Steps 4-5 in one `BEGIN…EXCEPTION` sub-block;
  the `IF NOT FOUND THEN RAISE PJ004` unwinds to the implicit savepoint → a *fresh* insert vanishes
  (test asserts `serve_model_charge` empty) and a *reclaim* restores the prior **expired** row (not a
  fresh lease). Correct per B7c.
- **Cap can't be raced.** The single conditional `UPDATE spend_ledger … WHERE reserved+actual+est <=
  cap` serializes on the one per-day PK row (same arbiter as `enqueue_job`/0011). Concurrent reserves
  serialize; the cap is a hard ceiling.
- **Grants / RLS / definer.** `serve_model_charge` force-RLS + service_role-only grants + no client
  policy; RPC `security definer set search_path=public`, `v_owner := auth.uid()` (never a param),
  granted `authenticated, anon`; owner derived internally; no `release_serve_model` (v5 DoS absent).
- **Config invariant consistent** across migration defaults, Task-1 tests, and Task-8: `magazine_est=6`,
  `K=5`, `daily_cap=500`; anon `2·5·6 = 60 ≤ 500·0.2 = 100`; registered residual documented as
  deferred-to-1G (not asserted bounded).

**Task 2 caps** — `withCaps(base, caps, max)` returns `base` unchanged when `caps` is undefined (local
skip verified, gemini.ts:37); `generateJson`'s 7-arg `opts?: { signal }` signature exists (gemini.ts:219);
`assertTranscribeInputWithinCap` precedent matches; the mocked `getGenerativeModel().generationConfig`
assertions line up with the real construction.

**Task 3 local parity** — `getPrincipal(outputFolder) === localPrincipal(outputFolder)`, so the new
`writeModelEnvelope(principal, …)` / `readModelEnvelope(principal, …)` call sites are behavior-identical
to the old `outputFolder`-keyed ones; `generatorVersion` is `.optional()` so pre-1F-a envelopes still
parse.

**Task 4 promote hardening** — the `exists(finalKey)`-first + move + re-check-on-error logic correctly
covers the concurrent over-TTL promoter race; uuid-prefixed staging matches `local-blob-store.ts:34`.

**Task 7 status mapping** — the `ResolveResult` union is exhaustively switched to HTTP codes; UUID
pre-validation precedes any DB call (no `22P02` 500); `type!=='summary'`→400; wrong-backend param→400;
committed→503 (not 404); promoted+blob-null→409 before any reserve/charge (matches M-2 in the spec).
`Video.language` is `z.enum(['en','ko'])` (types/index.ts:51) → the `resolveMagazineModel` call
typechecks.

---

## Convergence recommendation

Address **B-1** (mandatory — Task 5 won't compile), **H-1**, **H-2** before dispatch. Because B-1 lands
inside the Task-5 shared-code re-review trigger and H-1 mutates a shared schema, both fixes are
themselves new, unreviewed shared-code changes → **re-run the Task-5 dual review on the revised
render/theme/nav + render-dig-deeper set** per dev-process §Iterative Re-Review before marking Task 5
done. The money path (Task 1) needs no further round on the strength of this pass.

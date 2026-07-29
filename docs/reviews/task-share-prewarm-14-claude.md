# Claude adversarial review — `fix/share-prewarm-model-14` (backlog #14)

Independent Claude adversarial pass (parallel to `task-share-prewarm-14-codex.md`). Full money-path
trace against the actual reserve/settle SQL; leaf files confirmed untouched via `git diff`.

## Verdict: no Blocking / High / Medium. Three Low nits.

**MONEY — clean (verified, not asserted).** `warmSummaryModel` → `GET /api/html/<id>?playlist&type=summary`
→ `serveCloud` → `resolveAndParse` → `resolveMagazineModel` (`serve-doc.ts`): **a fresh model returns
`ok` before any `reserve` RPC or Gemini call** (pure blob read). Repeated "Create link" clicks do NOT
each charge — `reserve_serve_model` (`0020`) is idempotent per `(owner, doc_key, day)` with a 180s lease;
a second click within the lease → `in_flight` → `busy`/503 → warm returns `false`, no charge. Worst case
is `max_serve_attempts` (K=5) × 6¢/day, **identical to a normal owner view**. No new/double charge, no
budget bypass. `settle_serve_model` keeps the charge on success exactly as the view path does.

**SECURITY / invariant — clean.** Warm is a same-origin relative fetch to `/api/html`, which hard-requires
auth (401 otherwise) and owner-asserts the playlist. No anon path reaches generation. `git diff` confirms
`app/s/[token]/route.ts`, `lib/html-doc/read-model.ts`, `serve-doc.ts` are **byte-for-byte untouched** —
the never-charge leaf + `import-guard` invariant intact.

**CORRECTNESS — clean.** Token minted server-side by `createShare` *before* warm; warm is advisory and
cannot corrupt/block the token. `setShare` only after `await warmSummaryModel` settles. In-flight guard
(`inFlightRef`/`busy`) spans the whole op (cleared in `finally` after warm); double-click Create
early-returns; backdrop/Escape blocked during warm. `summaryHref` contract correct (`type=summary`, no
`format`/`download`). Warm `false` falls through to reveal with no `role=alert`.

**TEST QUALITY — sound.** S1 (deferred-promise) proves reveal-only-after-warm; S2/S3 pin the branches;
W1–W4 pin URL + true/false/no-throw. The `getByRole` → `toBeEnabled()` wait change is **necessary, not
masking**: Copy/Revoke are always present but `disabled={!share}`, so the old present-only wait resolved
before `share` was set (now set only after warm) and would have clicked a disabled button.

### Low findings — dispositions

| # | Finding | Disposition |
|---|---|---|
| Low-1 | Frozen dialog during a slow/hung first-time warm — no timeout/abort (also Codex **Medium**) | **FIXED** — `WARM_MODEL_TIMEOUT_MS` (15s) `AbortController` in `warmSummaryModel`; on timeout → abort → `false` → link revealed. Mutation-checked (neuter abort → hung-warm test red). |
| Low-2 | Fully silent warm failure — no client trace for a prod "share still 503s" report | **FIXED** — `console.warn` on both non-ok and catch paths (contract preserved: still returns `false`, never throws). |
| Low-3 | No explicit test that close/Escape is inert during CREATE+warm (only revoke path tested) | **FIXED** — added component test S4 (deferred warm → backdrop + Escape inert). |

## Codex Low (doc wording) — disposition
"fires at most once per doc" overstated the money invariant. **FIXED** — reworded the `warmSummaryModel`
doc comment, the plan's Global Constraints, and backlog #14 to: *fresh reads are free; absent/stale
generation is bounded by `reserve_serve_model` per owner/doc/day (same cap as an owner view).*

## Re-review scope
Fixes are **client-only** (a bounded timeout + a `console.warn` + a test + doc wording). They do **not**
touch the money/serve server path or the anon leaf that the money/security verdicts cleared. Per the
"small, contained change = one round" rule, no full re-review round was run; the timeout guard is
mutation-checked and the full suite is green (2489 / 250 suites, tsc clean).

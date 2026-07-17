# Round-5 Adversarial Re-Review — Reservation Release Lifecycle Spec v5 (Claude, independent)

**Artifact:** `docs/superpowers/specs/2026-07-15-reservation-release-lifecycle-design.md` (v5)
**Scope:** money path — hunt an **under-count** (a class-B/C error the classifier RELEASEs that could have metered). SQL bodies treated as settled (verified closed round-4, unchanged in v5); energy on §3.1 classifier + lib-layer reachability.
**Method:** grounded in `lib/gemini.ts`, `lib/gemini-cost.ts`, `lib/dig/generate.ts`, `lib/transcript-source.ts`, `lib/youtube.ts`, `lib/job-queue/{worker-runner,summary-handler}.ts`, `lib/ingestion/summary-core.ts`, `lib/html-doc/serve-doc.ts`, `node_modules/@google/generative-ai/dist/index.js`. Independent; did not read Codex output.

---

## Blocking

### B5-1 — `maybeMetered` misses `generateSummary`'s outer quality loop → a metered summary is RELEASEd (under-count)
**Where:** §3.1 `maybeMetered` enumeration (spec line 81) vs `lib/gemini.ts:359-368` (the `MAX_SUMMARY_ATTEMPTS` outer loop, =4 at `gemini-cost.ts:23`) and the wrapping catch at `gemini.ts:389-395`.

**The gap.** The C4-B1 fix sets `maybeMetered` **inside three inner retry loops only** (`generateJson` `:252-269`, `transcribeViaGemini` `:665-689`, dig `:256-266`). But `generateSummary` wraps `generateJson` in a **second, outer loop** the fix does not enumerate: each `attempt()` is a **fresh** `generateJson` with its own `maybeMetered` starting `false`; a successful outer attempt **returns — it never throws** — so its metering is captured by no thrown-error flag. `maybeMetered` only ever attaches to the *final* outer attempt's thrown error.

**Failure (inputs → wrong ledger):**
1. Outer attempt `i=0`: `generateJson` **succeeds** → Gemini metered a full generation → but the summary is incomplete / missing-▶ → no early return, loop continues (the *common* path — the whole reason the loop + `TIMESTAMP_MISS_CAP` exist).
2. Gemini now rate-limited/overloaded (a real partial outage).
3. Outer attempt `i=1`: inner loop gets HTTP **503** every inner attempt → `generateJson` throws 503 with **`maybeMetered=false`**.
4. Caught at `gemini.ts:389`, wrapped `{ cause: <503 fetch error, status:503, maybeMetered:false> }`.
5. Classifier: step 1 not our abort; step 2 `maybeMetered!==true`; step 3 `.status===503 ∈ {429,503}` → **`release`** → `fail_job(billable=false)` → **150¢ released**. But `i=0` metered a full generation → **under-count.**

**Reachability.** `GoogleGenerativeAIFetchError` sets `.status` (`index.js:272`) and is thrown with the real status (`index.js:434`). The multi-attempt outer path is normal (soft-miss re-rolls); a rate-limit ramp (early calls land, later throttle) is exactly the outage shape §1/behavior-2b/26 target. Under-count is **live the moment the class-A release flag is enabled** (the slice's goal), with **no dependency** on the deferred transcribe fallback. Round-4's "C4-B1 closed" was incomplete — the same vector, one loop level up.

**Direction.** Make the metering signal **job-granular**, not per-inner-loop: (a) `generateSummary` ORs `maybeMetered=true` on its thrown error whenever any prior outer attempt returned (`attemptsUsed>0` / `best!==null`); (b) §3.1 states the invariant generally — "any billable Gemini call that returned a body earlier in THIS job forces KEEP" — then enumerates every loop/sequence, not just the three inner loops. Add a behavior row distinct from 3e.

---

## Medium

### M5-1 — the same root cause latently affects the transcribe→summary→quickview call *sequence* (gated-safe in this slice)
**Where:** `summary-core.ts:69-85` (`resolveTranscriptSegments` → `generateSummary` → `extractQuickView`), each a separate billable call with its own `maybeMetered` scope.

- **quickview leg safe:** `extractQuickView` failures are swallowed (`summary-core.ts:122-133`) → job completes → KEEP.
- **transcribe→summary leg safe *only in this slice*:** with `CLOUD_TRANSCRIBE_FALLBACK_VERIFIED=false` (`gemini.ts:25`), `transcribeViaGemini` throws pre-billing. The moment that flag flips (deferred transcribe slice), a metered transcription then a `generateSummary` {429,503} throw is the same under-count across function boundaries.

**Direction.** The B5-1 fix (job-granular latch) should cover the whole billable *sequence*; note the transcribe leg as gated-safe-until-flag-flip so it isn't silently reintroduced. (Transitional — resolved by settle.)

---

## Low

### L5-1 — behavior-17 still lists "connection" as a class-A RELEASE trigger (contradicts v5 connection→KEEP)
§7 behavior 17 (spec line 354). CL4-H2 moved connection/DNS to class B → KEEP (SDK strips `.code`; `index.js:407-419`), and §3.1/§4/behavior-3f agree. Row 17 still names "connection" among serve class-A release triggers — un-implementable against a code-real shape and contradicts §9. If taken literally → serve under-count. Drop "connection" from row 17.

### L5-2 — tighten "no prior metered attempt" → "no billable call returned earlier in this job"
§7 rows 2b/2c + §3.1 situational table. The "no prior metered attempt" qualifier reads retry-scoped (invites the B5-1 too-narrow reading). Restate as job-scoped once B5-1 is fixed.

---

## Verified genuine (round-4 fixes hold, no new finding)
- **CL4-H1 (transcript typed-cause):** real bug at `transcript-source.ts:62`; `fetchTranscriptSegments` throws (`youtube.ts:102-104`) so `captionErr` truthy; the fix (preserve typed `geminiErr`) is adequate — with the fail-closed flag off, `geminiErr` is the pre-send `NonRetryableError` → correct RELEASE at $0. No surviving flattening point.
- **CL4-L1 (`ourSignal.aborted` necessary):** confirmed — `GoogleGenerativeAIError` never sets `.name` (`index.js:248-252`), so an SDK abort has `.name==='Error'`; only `ctx.signal.aborted` (`worker-runner.ts:30-32`) discriminates our lease-abort from an SDK timeout.
- **CL4-H2 (drop connection branch):** confirmed — connection errors surface as bare `GoogleGenerativeAIError`, no `.status`/`.code` → step 4 → KEEP (safe $0 direction); §9 correctly forbids a synthetic `{code}` test.
- **CL4-M1 (narrow {429,503}):** 500/502/504 excluded everywhere in the live spec, route to class-B KEEP — correct (500/502 can follow partial generation).
- **C4-H1 (typed dig error):** `generateDig` throws a status-less generic `Error` (`generate.ts:268-271`); the typed `GeminiHttpError{status}` is the right shape and reaches the classifier. Dig has no outer quality loop, so B5-1 doesn't recur on dig — provided dig's retry sets `maybeMetered` on a body-before-mid-stream-disconnect (worth a test; not a new finding since dig 500/502 already KEEP).
- **Consistency:** §1/§2.4/§3.1/§5/§6/§8/§9 + behaviors 2b/2c/3/3f/26 agree on {429,503}/connection→KEEP/`maybeMetered`→KEEP/dig-covered. Only live inconsistency: L5-1 (behavior-17). Change-logs §12-15 retain historical values — correct as history.
- **SQL bodies** (`fail_job`, cancel RPCs, `settle_serve_model`, `ledger_audit`): unchanged from round-4, no new concern. Serve has a single billable call, covered by inner-retry `maybeMetered`, not exposed to the B5-1 outer-loop gap.

---

## Verdict
One new Blocking (B5-1): the C4-B1 `maybeMetered` fix was scoped to the three inner retry loops and misses `generateSummary`'s `MAX_SUMMARY_ATTEMPTS` outer quality loop → a metered-but-imperfect early attempt then a final-attempt {429,503} is RELEASEd → under-count, live the instant the class-A release flag is enabled.

**NOT CONVERGED**

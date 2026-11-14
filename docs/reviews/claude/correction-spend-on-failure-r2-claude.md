# correction-spend-on-failure — round 2 — Claude half

Subject: `git diff origin/master...HEAD` on `fix/correction-spend-on-failure` (tip `dfae8b29`; the round-1
fold is `07e3f254`). Mandate: refute. Above all, can a press still spend without recording?

## What I ran (on this worktree, 2026-10-24)

| Check | Result |
|---|---|
| `npx tsc --noEmit` | rc=0 |
| `npx jest` over the 6 touched unit files (regenerate-cloud, regenerate, gemini-fix-summary, apply-core, regenerate-stamp, gemini) | 162/162 |
| `python3 scripts/check-function-revokes.py` | rc=0, 28 migrations; 0028 revokes PUBLIC and anon |
| Integration: `jest.integration.config.ts --runInBand` on `corrections-cloud` + `record-correction-spend`, env exported from the main checkout's `.env.test.local` (no file written into the worktree) | **23/23** on the shared local stack |
| `M4_PHASE=post bash scripts/check-schema-gates.sh` | rc=0, "all schema gates green". It ran while the Codex half was live on the same Postgres, and nothing looked inconsistent |
| SDK probe: `@google/generative-ai` 0.24.1, `generateContent` with a fetch stub that rejects on abort | measured, see H1 |

Confirmed sound, with no finding: (a) the `finally` runs once per request. There is one call site
(`regenerate-handlers.ts:364`) and no re-entry. `recordCorrectionSpend` cannot throw: `raceRpc` folds a
synchronous throw, a rejection and a `{error}` into the union, and the pricing is pure. (b) The only other
production caller of `fixSummary` is the LOCAL branch (`regenerate-handlers.ts:139`). It reads `.text` and
never read `usage`, so removing `usage` dropped nothing. (c) The response waits on the recording RPCs, which
run concurrently, so at most one 3 s deadline. (h) 0028 pins `search_path = public`, takes no argument,
derives the owner from `auth.uid()`, and reads the same `(now() at time zone 'utc')::date` day and the same
`guardrail_config` columns that 0026 enforces. It fails closed on a missing config row. (j) A failed press
now records a call, so it counts toward the limit, which is 0026's call-count semantics. Owner identity comes
only from the JWT, so one owner cannot exhaust another's allowance. (e) All five reasons are mapped, the type
is exhaustive, and the panel shows `data.error`. (i) The deploy order is stated in the 0028 header, on the
backlog closure and on the dashboard.

## Findings

### H1 — High — a press aborted (or timed out) while Gemini is generating records nothing and does not move the daily allowance. So the per-owner limit does not bound it.

- **Where:** `lib/gemini.ts:600`. The meter push happens only after `generateContent` *returns*.
  `lib/corrections/regenerate-handlers.ts:420` has `if (meter.attempts.length === 0) return;`.
- **Input:** a signed-in owner presses Correct and closes the connection (`request.signal` aborts) while
  the `generateContent` request is in flight. The same applies when the SDK's own
  `REQUEST_TIMEOUT_MS = 60_000` (`lib/gemini.ts:134`) fires, and that path is *retried*: up to 3 × 60 s
  in-flight calls.
- **What happens (code reading plus a measured SDK probe):** `generateContent` rejects, nothing is pushed,
  `applyCorrection` throws, the `finally` sees an empty meter and returns without an RPC. `correction_spend`
  is untouched, so `correction_allowance().calls` does not advance and the next press passes the new 429
  check. The press can be repeated without limit, and neither the per-owner counter nor `spend_ledger` ever
  sees it. That is the bound evasion backlog #62 was filed for, reached through abort instead of the
  validator.
- **The premise this rests on is UNVERIFIED:** that Gemini bills a request the client cancelled or timed
  out mid-generation. The branch's own docstring says it "is not observable from here". But round 1's H2
  disposition already decided the policy for exactly this kind of unknown: *billed, amount unknown, is
  charged at the bound, never dropped*. This path is the one place where that policy is not applied, and
  it is the one place where the *caller controls* the outcome. The backlog closure discloses
  "a `generateContent` that itself throws pushes nothing", but it does not say that this leaves the
  daily limit un-enforced for such presses, which is the consequence that matters.
- **Measured detail the fix depends on:** on SDK 0.24.1 both a caller abort and the SDK timeout surface
  as `GoogleGenerativeAIAbortError` with `name === 'Error'`, **not** `'AbortError'`:
  ```
  user abort -> name= Error ctor= GoogleGenerativeAIAbortError
  sdk timeout -> name= Error ctor= GoogleGenerativeAIAbortError
  ```
  So a fix keyed on `err.name === 'AbortError'` (the existing idiom at `gemini.ts:613`) would never fire.
- **Fix:** in `fixSummary`'s catch, push `{ promptTokens: null, outputTokens: null }` when the request was
  sent and then cancelled or timed out. Test for `err instanceof GoogleGenerativeAIAbortError ||
  opts.signal.aborted`. `meteredCorrectionCents` then charges `CORRECTION_WORST_ATTEMPT_CENTS` (3¢) and the
  call counts toward the allowance. Do NOT push for a `GoogleGenerativeAIFetchError` that carries an HTTP
  status (4xx/5xx): nothing was generated. Cases: a unit case where `generateContent` rejects with the
  real SDK abort error after the signal aborts, so the meter has one null attempt; and a route case where
  the abort happens mid-call and the RPC is called with `p_cents: 3`. If the team decides instead that
  cancelled calls are not billed, write that down as a measured premise on the row. As written, "not
  observable" is resolved in the under-count direction, which is the opposite of H2.

### M1 — Medium — the documented race is wider than stated: presses that slip past the limit are invisible to the global ledger too, and concurrency is unbounded

- **Where:** backlog #61's 2026-10-24 amendment and #62's closure ("the per-owner bound is N +
  concurrency"). Mechanism: `0026_record_correction_spend.sql:94`. The per-owner refusal `raise`s
  *before* the `spend_ledger` update below it, so the whole call rolls back.
- **Input:** K concurrent presses at `calls = N-1`.
- **What happens (code reading):** all K pass `correction_allowance`, all K pay Gemini, one recording
  lands, and K-1 RPCs raise "owner daily correction limit reached". Their spend reaches neither counter,
  including the 5000¢ global ledger. No rate limit fronts `app/api/videos/[id]/regenerate/route.ts` (grep
  for `rate.?limit` hits only dig/jobs), so K is whatever the client chooses: ≤9¢ × K, unrecorded. "N +
  concurrency" reads as a small bounded overshoot. It is unbounded, and it is unrecorded.
- **Fix:** state both facts on backlog #61 and in the dashboard's "still open" paragraph. Optionally, and
  cheaply: a follow-up migration could make the per-owner refusal still write `spend_ledger`, since it
  records money already spent, which keeps the global cap truthful even when the per-owner bound is
  exceeded. That is a semantics change to 0026, so it is a decision for #61, not for this fold.

### L1 — Low — the dashboard says "every paid try is recorded"

- **Where:** `docs/dashboard-entries.md`, the 2026-10-24 entry, second paragraph.
- That is not true for H1's path. The backlog closure is accurate ("every **returned** attempt"). The
  plain-language entry drops the qualifier. **Fix:** "every try Gemini answered is recorded", or close H1.

### L2 — Low, pre-existing — `fixSummary`'s "preserve AbortError identity" rethrow is dead for an in-flight abort

- **Where:** `lib/gemini.ts:613` (also `:437`, `:701`).
- Measured above: the SDK re-wraps the fetch's `AbortError` as `GoogleGenerativeAIAbortError` with
  `name === 'Error'`. An abort during the call is therefore treated as a retryable failure. The loop-top
  guard or the abortable backoff stops a second paid call, so there is no money consequence (UNVERIFIED
  for the last-attempt path, where it falls through to "Gemini summary fix failed" and a 500). This is
  recorded because H1's fix must not reuse that idiom. File it separately; it is not this branch's defect.

## Not findings, checked

- Chunking at the per-call ceiling: under `CORRECTION_CAPS` a press is ≤9¢ against 12¢, so it is one call.
  The split only matters after a config or price change, and it then spends extra daily calls, which is the
  over-count direction, as documented. The chunks race each other at `calls = N-1` and the loser is
  refused. That is the same M1 mechanism and only under a changed config.
- Tests: the `fixSummary` mocks in `regenerate-cloud.test.ts` model the meter contract (push before the
  throw), and `gemini-fix-summary.test.ts` drives the real `fixSummary` against a mocked SDK at the
  `lib/gemini.ts` boundary, so the meter push itself is tested on real code. The integration 429 case goes
  through the real 0028. No test covers an abort *during* `generateContent` with the real SDK error class.
  That is H1's missing case.

VERDICT: NOT CONVERGED

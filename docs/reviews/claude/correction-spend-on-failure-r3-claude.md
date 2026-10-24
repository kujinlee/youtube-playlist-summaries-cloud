# correction-spend-on-failure — round 3 — Claude half

Subject: `git diff origin/master...HEAD` on `fix/correction-spend-on-failure` at `d5f3e823`. The main
subject is the round-2 fold `402ea6f5`, plus the master merge `9b9f00e1`. Mandate: REFUTE.

## What I ran

| Check | Result |
|---|---|
| `npx tsc --noEmit` (worktree) | clean (`TSC_OK`) |
| `npx jest` on the touched unit files (8 suites) | 136 / 136 pass |
| Full `npx jest --ci --json` (output sent to scratchpad, not the worktree) | **2932 tests / 279 suites, 0 failed**. That matches the roadmap line the branch edits |
| `python3 scripts/check-function-revokes.py` | green, 28 migrations |
| A rolled-back probe of 0028 on the local `supabase_db` (role `authenticated`, jwt claims set) | `anon` EXECUTE = f, `authenticated` = t. Allowance read `{"calls":0,…}`. Then `record_correction_spend(9)` and `record_correction_spend(0)`. Allowance read `{"calls":2,"max_calls":8,"max_cents":12}`. `ROLLBACK`. The probe gave consistent results |
| A real-SDK probe of `@google/generative-ai` 0.24.1 against a local HTTP server, on Node 20.18.2 and Node 22.14.0 | see F1 |
| `scripts/check-schema-gates.sh` and the integration files | **NOT RUN.** I did not run them because they write to the Postgres the Codex half is using at the same moment. The unit ceiling test and the 0026/0028 read below cover (k) and (h) |

## Findings

### F1 — Low — a timeout during the response-BODY read is not metered, and it is surfaced as a client cancellation

`lib/gemini.ts:609`. The input is the SDK's own `timeout` (`REQUEST_TIMEOUT_MS`, 60s) firing after the response headers have arrived but before `response.json()` has finished.

The round-2 comment says: *"MEASURED on SDK 0.24.1: a caller abort AND the SDK's own timeout both reject with GoogleGenerativeAIAbortError"*. That holds only for the **fetch** phase. In `node_modules/@google/generative-ai/dist/index.mjs`:
- `makeRequest` (`:392-404`) wraps only `await fetchFn(...)`.
- `generateContent` (`:864-867`) then calls `await response.json()` **outside** that wrapper.
- The timeout timer (`buildFetchOptions`, `:443-445`) aborts the same controller whatever phase the request is in.

I measured it. The server sent a 200 status and half the JSON body, then stalled. The call used `timeout: 500` and the caller's signal was never aborted:

```
node 22.14.0: name= AbortError ctor= DOMException isSDKAbort= false callerAborted= false msg= This operation was aborted
node 20.18.2: (identical)
```

So in `fixSummary`:
- **The inner catch (`:609`):** the error is not `instanceof GoogleGenerativeAIAbortError`, and `opts.signal.aborted` is false. **Nothing is pushed to the meter.**
- **The outer catch (`:633`):** `name === 'AbortError'` matches, so the error is rethrown as a cancellation. There is no retry. The route returns a 500.
- **The route's `finally`:** if this was the first attempt, `meter.attempts.length === 0`, so nothing is recorded and no daily slot is consumed.

A status line has arrived, so the request was served, and it was presumably billed. That last part is UNVERIFIED: I cannot observe Google's billing.

**Severity and reach:**
- The client cannot trigger this. The timer is ours, and the window needs Google to send headers and then stall the body.
- For non-streaming `generateContent`, the headers usually follow the finished generation, so the window is small. I did not measure that half of the claim against real Gemini.
- This is **not fold-induced**. Before round 2 this path was also unmetered and was also rethrown as AbortError. The fold's measurement simply covered one phase and was described as covering both.

**What is wrong, and should change:**
- The code comment at `:606-608`.
- The dashboard sentence *"Tries cut off part-way because … the request timed out … are also counted"* (`docs/dashboard-entries.md`, 2026-10-24 entry), which overclaims the same way.
- The tests in `tests/lib/gemini-fix-summary.test.ts` mock `generateContent` to reject with `GoogleGenerativeAIAbortError` for the timeout case. That encodes the contract exactly as imagined, which is section (f)'s concern.

**Fix (two lines):**
1. Meter on `err instanceof GoogleGenerativeAIAbortError || (err as {name?:string})?.name === 'AbortError' || opts.signal.aborted`.
2. In the outer catch, rethrow as a cancellation only when `opts.signal.aborted`. That lets a body-phase timeout retry the way a fetch-phase timeout does.
3. Add a case that throws `new DOMException('This operation was aborted', 'AbortError')` while the signal is NOT aborted.

### F2 — Low — the ceiling test's "no other migration sets it" scan misses two valid SQL forms

`tests/lib/corrections/correction-ceiling.test.ts`, the `setters` regex. I ran it against these inputs:

```
false | update public.guardrail_config set correction_max_cents = 5 where id
false | alter table guardrail_config alter correction_max_cents set default 5
true  | update guardrail_config set correction_max_cents=5
true  | alter table public.guardrail_config alter column correction_max_cents set default 5
```

- Postgres allows `COLUMN` to be omitted, and the repo does use schema-qualified `public.` names (0019, 0020). A later migration written in either of the two forms the regex misses would leave this test green over a lowered ceiling. The repo's own precedent, `0022:23-24`, uses the caught forms.
- The integration case `record-correction-spend.int.test.ts:138` still covers the live row.
- On (k): the test does read the real 0026 (`declaredCeiling()` parses `0026_record_correction_spend.sql:30`, `default 12`), not a copy. A drop-and-re-add in a later migration is caught by the `toEqual(['0026_…'])` file check.

**Fix:** make the scan `(public\.)?guardrail_config` and `alter\s+(column\s+)?correction_max_cents`, or more simply, fail on ANY occurrence of `correction_max_cents` in a migration other than 0026 and 0028 (0028 is a reader). Add an adjacent negative case for each of the two forms.

### F3 — Low / report only — (m) the two other dead name-check sites in `gemini.ts` cost no money today

- **The sites:** `lib/gemini.ts:437` (`generateSummary`), `:722` (magazine), and the same idiom at `lib/transcript-source.ts:59`.
- **The mechanism:** `generateJson` has no abort rethrow. On the LAST attempt, an in-flight caller abort ends with `throw lastErr` (`:314`). That error is a `GoogleGenerativeAIAbortError` whose `name` is `'Error'`, so these checks miss it and the error gets wrapped.
- **Why the worker is unharmed:** the worker never keys on the name. `classifyGeminiFailure` returns `'keep'` first on `ourSignal?.aborted` (`lib/gemini-failure.ts:77`). Release, retryability and the `metered` latch are therefore unaffected. The outcome is a misleading message ("Gemini summary failed: Request aborted…") on a deliberate shutdown, and comments that claim a protection that does not fire.
- **F1's mirror image:** a body-phase timeout on generateJson's last attempt is a DOMException named AbortError, so `:437` would rethrow a timeout *as* an abort. This is also money-neutral, because the classifier keys on the signal and not the name.
- **Recommendation:** file it, do not fold it here.

## Mandate items with no finding

- **(a) and (l), every path.** I traced these by reading `fixSummary` (`lib/gemini.ts:590-644`) and `serveCloud` (`lib/corrections/regenerate-handlers.ts:234-364`). The only gap is F1.
  - A returned attempt is pushed before `assertNotTruncated` and the empty check.
  - A caller abort in flight, on any attempt including the last, is pushed once at `{null,null}` and rethrown as `DOMException('AbortError')` by the signal check at `:634`.
  - An abort during the backoff rejects out of `abortableSleep` from inside the catch, with no push. That is correct, because no call was in flight.
  - The loop-top check prevents a paid call after an abort.
  - An HTTP 4xx/5xx is not pushed. That is stated as open in the dashboard.
  - The `finally` runs exactly once per request. `meter` is a request-local, so nothing re-enters it.
  - Refusals with status 401/400 return before the `try`. The early returns inside it (404, 429, 503) reach the `finally` with an empty meter and record nothing.
  - **Over-count direction:** a non-abort network error that coincides with an aborted signal is charged 3¢. That over-counts, which is the safe direction.
- **(b) other callers.** The LOCAL branch (`regenerate-handlers.ts:139`) calls `fixSummary` with no meter (`meter?` is optional) and reads only `.text`. No caller read the removed `usage`, and `tsc` is clean.
- **(c) recording cannot fail the request.**
  - `raceRpc` folds a throw or a rejection into the union and always clears its timer (`lib/serve-rpc.ts:42-77`).
  - `recordCorrectionSpend` cannot throw: `meteredCorrectionCents` and the log formatting are pure.
  - The response waits at most `CORRECTION_RPC_TIMEOUT_MS` (3s). A failure is logged with the owner, the video and the cents, and it is never retried. The dashboard states that last point.
- **(d) the RPC contract.**
  - One call per press. The worst case is `3 × ceil((12192·30 + 8192·250)/1e6) = 3 × 3 = 9¢`, below 12¢.
  - A 0¢ record is accepted (`p_cents < 0` is the lower guard) and consumes a slot. My probe confirmed it.
  - Failed presses count toward N, and that is what the 0026 row intends ("both only ever count successes" is the defect).
- **(e) and #63.** `Record<StructuralFailureReason, …>` is exhaustive by type, and all five reasons map to a 422 next to the 413. `CorrectionsPanel.tsx:63-64` renders `data.error` for any non-ok status, including 429 and 503.
- **(h) migration 0028.**
  - The owner comes from `auth.uid()` and is not a parameter.
  - `search_path = public` matches the 43-site repo convention.
  - The day expression `(now() at time zone 'utc')::date` is the same as 0026's (`:42`).
  - The revokes are complete (guard green, and the probe shows anon = f).
- **(i) deploy order.** The order is stated in the migration header and in the dashboard entry.
- **(j) the 429.** It counts recorded presses, failed ones included. Another owner's allowance cannot be exhausted, because both RPCs derive the owner from `auth.uid()`.
- **(g) the backlog.** The #62 and #63 closures and the #61 revert are accurate apart from F1's overclaim. The roadmap counts match the suite (2932 / 279).

## Thrashing check

None of F1-F3 was caused by the round-2 fold's own fix. F1 is a phase the fold's measurement did not cover, and the same behaviour existed before the fold. Per the round-2 coordinator's arming note, round 3 carries **no fold-induced finding**.

VERDICT: CONVERGED

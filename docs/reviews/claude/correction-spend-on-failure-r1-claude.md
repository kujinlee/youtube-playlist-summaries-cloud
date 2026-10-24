# correction-spend-on-failure — round 1 — Claude half

Subject: `git diff origin/master...HEAD` on `fix/correction-spend-on-failure` (commits `02006acf`, `7c035a01`).
Mandate: refute. Above all, can money still be spent without being recorded, or recorded twice?

## What I ran

- `npx jest` on the five touched unit files: **5 suites, 101 tests, all passed**.
- `npx tsc --noEmit`: **rc=0**.
- A probe of `record_correction_spend` on the **local** Supabase DB (`supabase_db_…` container), run as
  `authenticated` for one existing profile, inside `begin … rollback` (nothing persisted). Script:
  `scratchpad/b2r1-probe.sql`. Output below, under H1.
- **Not run:** the integration files. The Codex half shares this stack, and both `corrections-cloud`
  cases assert on a **global** `spend_ledger` delta, so a concurrent run could produce a false red or
  a false green. I am relying on the implementer's 17/17 for those and have not re-measured it.

## Findings

### H1 — High — after the owner's 8th recorded press of the day, every billed press is spent and recorded NOWHERE, and the closure says "every paid try is counted"

**Where:** `supabase/migrations/0026_record_correction_spend.sql` (the `v_claimed = 0` → `raise`
branch), `lib/corrections/regenerate-handlers.ts` `serveCloud` (no pre-call check) and
`recordCorrectionSpend` (logs and swallows the raise). The overclaim is in `docs/dashboard-entries.md`
(2026-10-24 entry) and the backlog #62 closure in `docs/backlog.md:90`.

**Input:** one owner presses a correction that the validator refuses (for example "delete the
intro") ten times in one UTC day.

**What happens, measured on the local DB (rolled back):**

```
NOTICE:  press 1 recorded
...
NOTICE:  press 8 recorded
NOTICE:  press 9 NOT recorded: record_correction_spend: owner daily correction limit 8 reached
NOTICE:  press 10 NOT recorded: record_correction_spend: owner daily correction limit 8 reached
 calls | cents
-------+-------
     8 |     8
```

The per-owner limit in 0026 bounds what is **written to the ledger**. It does not bound **spending**,
because nothing reads `correction_spend` (or `spend_ledger`) before `fixSummary` is called. A
`grep -rn "correction_spend\|spend_ledger\|daily_cap"` over `lib app worker components` finds no reader
on the correction path. `loadSummaryForServe` returns `over_budget` only for the serve/refresh budget.
So from press 9 on, Gemini is billed, the RPC raises, `recordCorrectionSpend` logs
`[correction-spend] FAILED to record … limit 8 reached`, and the response is unchanged. The loop
backlog #62 describes ("a caller can spend in a loop while every guardrail reads zero") still exists.
The only change is that the guardrails now read at most 96¢ per owner per day instead of 0, while
actual spend has no limit.

This is not a regression. Before the branch, successes past the 8th were already unrecorded the same
way. But the branch makes two things worse or false:

1. **The closure and dashboard overclaim.** "Now every paid try is counted, whether the correction
   worked or not" is false from press 9. "a person could keep spending while every counter read zero"
   is presented as fixed, but the spending part is not.
2. **Failures now use up the owner's 8 slots**, so after 8 refused presses the owner's later
   successes also go unrecorded. This answers mandate (d). Recording a failure never **blocks** a
   later success, because the limit blocks nothing. It **hides** the later success from the ledger
   instead.

It also loses the decision-log bet in `7c035a01`: "no path where a billed attempt goes unrecorded".

**Fix:** pick one; the coordinator decides.
- (a) **Close the loop in this branch.** Refuse the press before any paid call when the owner's
  `correction_spend.calls` for today is at or over `correction_max_calls_per_owner_day`: return a 429
  with a code such as `correction-limit-reached`. This needs a small SECURITY DEFINER read or check
  RPC, because `correction_spend` is service_role-only. It is still a race (two concurrent presses
  at 7 both proceed), but that is bounded at N + concurrency, not unbounded. Reserve/settle remains
  backlog #61.
- (b) **Keep the code as it is, and re-scope the text.** The backlog #62 closure and the dashboard
  entry should say that recording now covers failures and retries **up to the per-owner limit**,
  that past the limit spend is neither recorded nor refused, and they should file that as a new 🔴
  row (or fold it into backlog #61 with its trigger). Then "closes the leak" stops being claimed.

### M1 — Medium — the response now waits on the spend RPC on every paid path, with no timeout

**Where:** `regenerate-handlers.ts`, `finally { await recordCorrectionSpend(...) }`.

**Input:** PostgREST/RPC slow or hung while a press is refused or fails.

**What happens (UNVERIFIED, read from code):** a `finally` that awaits delays the settled `return`
value until it completes. Before the branch, only the success path awaited this RPC. Now the 422, the
500 and the abort paths do too. `supabase-js` sets no default request timeout, so a hung RPC holds the
response until the route's `maxDuration`. That contradicts the spirit of "recording never fails the
request": a request that times out has failed from the user's point of view. No test covers a slow RPC.

**Fix:** race the RPC against a short timer (for example 2–3 s) and log `TIMED OUT` on loss. That
keeps the attempt recorded in the normal case and bounds the latency it can add. Alternatively, use
Next's `after()` for post-response work, after checking the bundled Next docs, since this repo's Next
differs from the standard one.

### L1 — Low — a press whose summed attempts exceed 12¢ records nothing at all

`record_correction_spend` rejects rather than clamps when `p_cents > correction_max_cents`. Before the
branch, a press reported at most one attempt (≤3¢ under `CORRECTION_CAPS`). Now it reports up to 3
(≤9¢). That is still inside 12¢ by 0026's own derivation, so this is not reachable today. But the
headroom is now 3¢ instead of 9¢, so a price change or a cap change hits it sooner, and the failure is
total (0¢ recorded, one `console.error`) rather than partial. Worth one line in the
`meteredCorrectionCents` comment, or a cap-soundness assertion on the **sum** of `retries + 1`
attempts if the existing one asserts only a single call. I did not check which the existing test does.

### L2 — Low — the preflight-413 unit case injects the error from the wrong function

`tests/api/regenerate-cloud.test.ts`: "records nothing when no attempt was billed — the preflight
refused" makes `fixSummary` reject with the `NonRetryableError`. In production that error comes from
`assertCorrectionInputWithinCap`, which runs before `fixSummary`. The assertion (empty meter → no RPC)
still holds, so the case is not wrong. But it passes because the mock pushes nothing, not because the
preflight ran first. If someone later moved metering ahead of the preflight, this case could not see
it. Make `assertCorrectionInputWithinCap` throw instead.

### L3 — Low — the integration cases assert on a global ledger delta

`corrections-cloud.int.test.ts` (#62 case, and the existing §7 case) read `spend_ledger.actual_cents`
before and after and expect +1. Any other writer on the same day, such as a concurrent review half or
another integration file, breaks this. The pattern already existed. Noted only because two reviewers
were told they may run it concurrently.

## Checked and found sound

- **(a) Paths.** Success, validator refusal, exhausted retries (truncation and empty content), blob
  failure, `updateVideoFields` failure, and an abort during backoff all reach the single `finally` with
  the meter intact. Each attempt is pushed once, at `lib/gemini.ts`, directly after `generateContent`
  and before both retry triggers. The meter is created per request, so a retried HTTP request gets a
  fresh meter, and there is one `finally` per invocation, so it cannot double-record. Early returns
  (401/400/404/409/503) leave the meter empty and record nothing. `recordCorrectionSpend` cannot throw:
  the only code outside its `try` is pure arithmetic and `console.warn`.
- **(a) Abort inside `generateContent`** pushes nothing. This is stated in the `UsageMeter` doc and the
  report as unobservable, and I agree it is out of reach here.
- **(b) Callers.** `fixSummary` has two callers, the local branch (`regenerate-handlers.ts:132`, which
  reads `.text` only, so it is unaffected) and `applyCorrection`. Nobody else read the removed `usage`.
  `actualCents` had one reader, the deleted inline RPC.
- **(d) Arguments.** `p_cents` is the sum of per-attempt `Math.ceil`, which matches 0026's 3 × 3¢
  derivation. Each press counts once in `calls`, whatever the number of attempts. A press whose
  attempts are all unmeasured records nothing and warns, rather than recording 0.
- **(e) backlog #63.** All 5 `StructuralFailureReason` values are mapped, and the map is exhaustive
  by type. The 422 has the same `{error, code}` shape as the 413. `CorrectionsPanel.tsx:63-64` renders
  `data.error`. The local branch never runs the structural validator, so it has no unmapped path.

## Verdict

H1 is a path where billed attempts go unrecorded without limit, and the branch's own closure text
claims the opposite. It needs either the pre-call refusal or a re-scoped closure plus a filed row
before this converges.

VERDICT: NOT CONVERGED

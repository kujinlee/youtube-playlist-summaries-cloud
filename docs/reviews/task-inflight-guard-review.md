# In-flight-job guard (backlog #17, partial) — Claude review + Codex adjudication

Claude half of the dual review. Codex half: `task-inflight-guard-codex.md` (ran on `gpt-5.5`; the
wrapper fell through `gpt-5.6-sol → -terra → -luna` on HTTP 400).

**Verdict: converged.** Codex's Blocking was real, was confirmed by reading the code, and is fixed.
Its Low was real and is fixed. Its High is a correctly-identified *limit* of a deliberately partial
mitigation, not a defect in it — adjudicated below and now documented in the code.

---

## Codex Blocking #1 — a swept job can still have a live worker. **CONFIRMED, FIXED.**

Verified rather than accepted. `sweep_expired_leases` (`0008:167-181`) takes an `active` job whose
lease expired and sets:

```sql
status = case when j.cancel_requested then 'cancelled'
              when j.attempts >= j.max_attempts then 'dead_letter'
              else 'queued' end,
locked_by = null, lease_token = null, lease_expires_at = null
```

So a job at max attempts goes straight to `dead_letter` with its lease columns cleared — while the
worker that claimed it may still be inside a Gemini call holding the `base` it pinned. The queue says
finished; the process is not. The original guard probed only `queued`/`active` and would have
relocated straight through it.

**Fix:** `dead_letter` and `cancelled` also block, but only while *recently* swept. The bound is
`worker-runner.ts:45`'s `wallClockMs` (600 000 ms) — derived, not invented: no worker outlives its
claim by more than that, and measuring from the sweep's `updated_at` is conservative because the
worker started before the sweep.

**Bounding it was not optional.** Blocking on `dead_letter` unconditionally would stop a video's base
ever being repaired — trading a narrow race for a permanent stall. Both directions are tested:
blocks when recent, stops blocking past the bound.

**What this sharpened, and the more valuable output than the fix itself:** the selection rule is not
"has this job written?" but **"can this job write AFTER the relocation has enumerated the old base?"**
That is why `completed` and `failed` genuinely do not block — whatever they wrote is already under
the old base, so `paidKeysUnder` finds it and the relocation carries it along. The rule is now
written down in `in-flight-job.ts` so the next person extending the status list has a criterion
instead of a list to copy.

## Codex High #1 — the residual window is not milliseconds. **CONFIRMED, and I had it wrong.**

I wrote "a residual millisecond window remains". That was wrong, and I found it independently while
tracing the same question. Between the probe and the metadata write sit `paidKeysUnder` (a `list`),
plan construction, **N sequential blob copies** (MD + model + one per dig), and a freshness re-read.
On a remote Supabase with a well-dug video that is seconds, not milliseconds.

**Adjudicated as a limit, not a defect.** It is not a regression — before this change the entire
minutes-long window was unguarded — and no reordering fixes it, because the hazard is a job
*enqueued and claimed* after the probe. Only a compare-and-swap on the serial in `persist_summary`
closes it, which is backlog #17's durable fix and explicitly out of scope here.

The comment is corrected to state the real bound: exposure shrinks from *the whole minutes-long
Gemini run of an already-active job* to *the duration of this relocation's copy phase*. A large
reduction, not an elimination. Overstating it was the actual risk.

## Codex Low #1 — playlist lookup scoped by key alone. **CONFIRMED, FIXED.**

`playlist_key` is unique only per owner (`0001:17`). Under a user JWT, RLS already narrows the
lookup, so this was harmless in production — but the function accepts any `SupabaseClient`, and a
service-role caller doing a key-only lookup either fails `maybeSingle()` on an ambiguous match or
binds another tenant's playlist id and then counts the wrong tenant's jobs. Now scoped on
`(owner_id, playlist_key)`.

**And the fix initially had zero coverage.** Mutation-testing it (delete the `owner_id` predicate)
left all 8 tests green, because every test used a user JWT where RLS makes the predicate redundant.
That is dead defense-in-depth — worse than nothing, because it reads as load-bearing. Added a test
using the service-role client with the same `playlist_key` under two owners; the mutation now kills
it.

---

## Claude finding — `dead_letter` was an untested status

The first status test enumerated `queued/active/completed/failed/cancelled` and missed
`dead_letter`, which is in the CHECK domain
(`queued, active, completed, failed, dead_letter, cancelled`). Found by reading the constraint rather
than the code. The test now enumerates the **complete** domain deliberately, so a status added later
forces a decision here instead of defaulting to "does not block".

## Mutation record — 7 mutations, all killed

| # | Mutation | Result |
|---|---|---|
| 1 | delete the in-flight refusal | 3 tests red |
| 2 | fail **open** on an unreadable probe | 1 red |
| 3 | let a throwing probe escape | 1 red |
| 4 | treat `completed` as pending | 1 red |
| 5 | drop the playlist scoping | 1 red |
| 6 | filter to `summary` jobs only (reopens the dig window) | 1 red |
| 7 | fail **open** when the playlist cannot be resolved | 2 red |
| 8 | ignore swept rows (the pre-Codex behaviour) | 1 red |
| 9 | no recency bound on swept rows (permanent stall) | 2 red |
| 10 | drop the `owner_id` scoping | green → **test added** → 1 red |

Row 10 is the one worth remembering: it passed in both worlds until a test was written for the caller
shape where it matters.

## Process note

`git checkout --` reverted uncommitted work during mutation testing for the **third** time on this
project, despite the dev-process rule ("commit the fix before mutating"). The swept-status
implementation had to be reapplied from scratch. The rule is right; I broke it because the fix felt
too small to commit first. Size is not the criterion — *whether a checkout is coming* is.

## Gates

tsc clean · 2596 unit tests · 9 probe integration tests · full integration green twice back-to-back
with no DB reset between.
